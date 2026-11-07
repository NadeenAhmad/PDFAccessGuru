"""
Tables. A table holds rows (TR), optionally grouped into THead, TBody and TFoot, plus one
caption; a row holds header cells (TH) and data cells (TD).

Repairs keep the table's shape:
- loose cells are put into rows by their position on the page (cells on the same line form one
  row); without positions, by the number of columns of the table's other rows;
- content that sits inside a cell's area on the page joins that cell;
- other content at the start or end of a table becomes its caption (if it reads like one,
  e.g. "Table 3: ...") or is moved just outside the table; in the middle it becomes a row
  with one cell across all columns, so the column count stays the same;
- empty tags are removed, and grouping tags (Div, Span, ...) around rows or cells are removed.
"""

from __future__ import annotations

import re

from pikepdf import Array, Dictionary, Name, Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.layout import Layout
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import (
    Roles, has_content, index_of, is_element, kids, move, new_element, set_kids,
)

ROW_GROUPS = ("THead", "TBody", "TFoot")
CELLS = ("TH", "TD")
_WRAPPERS = ("Div", "Span", "NonStruct", "Part", "Sect", "Art")
_CAPTION_TEXT = re.compile(r"^\s*(?:table|tab\.|tabelle|tableau|tabla|tabella)\b", re.IGNORECASE)


class CellsWithoutRows(Exception):
    """Loose cells whose rows cannot be worked out (no positions and no column count)."""


def _colspan(cell) -> int:
    attributes = cell.get("/A")
    entries = list(attributes) if isinstance(attributes, Array) else [attributes]
    for entry in entries:
        if isinstance(entry, Dictionary) and entry.get("/O") == Name("/Table") and "/ColSpan" in entry:
            try:
                return max(1, int(entry["/ColSpan"]))
            except (TypeError, ValueError):
                return 1
    return 1


class TableRepair:
    def __init__(self, pdf: Pdf):
        self.pdf = pdf
        self.roles = Roles(pdf)
        self._layout: Layout | None = None

    @property
    def layout(self) -> Layout:
        if self._layout is None:
            self._layout = Layout(self.pdf)
        return self._layout

    # --- reading the table -------------------------------------------------------------

    def table_of(self, element) -> Dictionary | None:
        current = element
        for _ in range(8):
            if not is_element(current):
                return None
            if self.roles.is_(current, "Table"):
                return current
            current = current.get("/P")
        return None

    def rows(self, table) -> list:
        found = []
        for part in kids(table):
            if self.roles.is_(part, "TR"):
                found.append(part)
            elif self.roles.of(part) in ROW_GROUPS:
                found.extend(row for row in kids(part) if self.roles.is_(row, "TR"))
        return found

    def column_count(self, table) -> int | None:
        """The most common number of columns among the table's rows."""
        if table is None:
            return None
        counts = [sum(_colspan(cell) for cell in kids(row) if self.roles.of(cell) in CELLS)
                  for row in self.rows(table)]
        counts = [count for count in counts if count > 0]
        if not counts:
            return None
        return max(sorted(set(counts), reverse=True), key=counts.count)

    def _cell_at(self, part, owner, candidates) -> Dictionary | None:
        """The cell whose area on the page contains the middle of the part, if any."""
        box = self.layout.box(part, owner)
        if box is None:
            return None
        x, y = box.center
        for candidate in candidates:
            cells = kids(candidate) if self.roles.is_(candidate, "TR") else [candidate]
            for cell in cells:
                if self.roles.of(cell) not in CELLS:
                    continue
                cell_box = self.layout.box(cell)
                if cell_box is not None and cell_box.page == box.page and cell_box.contains_point(x, y):
                    return cell
        return None

    def group_cells(self, cells: list, owner, columns: int | None) -> list[list]:
        """Split loose cells (in reading order) into rows."""
        boxes = [self.layout.box(cell, owner) for cell in cells]
        if any(box is not None for box in boxes):
            rows: list[list] = []
            reference = None                      # first positioned cell of the current row
            for cell, box in zip(cells, boxes):
                if rows and (box is None or reference is None or reference.vertical_overlap(box) >= 0.5):
                    rows[-1].append(cell)
                    reference = reference or box
                else:
                    rows.append([cell])
                    reference = box
            return rows
        if columns and len(cells) % columns == 0:
            return [cells[i:i + columns] for i in range(0, len(cells), columns)]
        raise CellsWithoutRows()

    def _continuing_cells(self, row: Dictionary, run: list, owner, columns: int | None) -> int:
        """How many of the loose cells at the start of the run belong to the row before them."""
        row_box = self.layout.box(row)
        boxes = [self.layout.box(cell, owner) for cell in run]
        if row_box is not None and any(box is not None for box in boxes):
            count = 0
            for box in boxes:
                if box is None or row_box.vertical_overlap(box) < 0.5:
                    break
                count += 1
            return count
        if columns:
            present = sum(_colspan(cell) for cell in kids(row) if self.roles.of(cell) in CELLS)
            return max(0, min(columns - present, len(run)))
        return 0

    # --- rebuilding --------------------------------------------------------------------

    def _unwrap(self, container: Dictionary, parts: list, allowed: tuple[str, ...]) -> tuple[list, bool]:
        """Replace grouping tags that only hold allowed table parts by those parts."""
        result, changed = [], False
        for part in parts:
            inner = kids(part)
            if (self.roles.of(part) in _WRAPPERS and inner
                    and not any(key in part for key in ("/Alt", "/ActualText", "/E", "/ID"))
                    and all(self.roles.of(kid) in allowed for kid in inner)):
                result.extend(move(self.pdf, inner, part, container))
                changed = True
            else:
                result.append(part)
        return result, changed

    def _new_row(self, container: Dictionary, cells: list, owner: Dictionary) -> Dictionary:
        row = new_element(self.pdf, "TR", container, like=owner)
        set_kids(row, move(self.pdf, cells, owner, row))
        return row

    def _full_width_row(self, container: Dictionary, part, owner: Dictionary, columns: int | None) -> Dictionary:
        row = new_element(self.pdf, "TR", container, like=owner)
        cell = new_element(self.pdf, "TD", row, like=owner)
        if columns and columns > 1:
            cell["/A"] = Dictionary({"/O": Name("/Table"), "/ColSpan": columns})
        set_kids(cell, move(self.pdf, [part], owner, cell))
        set_kids(row, [cell])
        return row

    def repair_group(self, container: Dictionary) -> bool:
        """Repair a Table, THead, TBody or TFoot so it holds only what it may hold."""
        is_table = self.roles.is_(container, "Table")
        table = container if is_table else self.table_of(container)
        columns = self.column_count(table)
        valid = ("TR", "Caption") + ROW_GROUPS if is_table else ("TR",)
        parts, changed = self._unwrap(container, kids(container), valid + CELLS)
        rows_kinds = ("TR",) + ROW_GROUPS
        has_caption = any(self.roles.is_(part, "Caption") for part in kids(table)) if table is not None else True
        result: list = []
        outside_before: list = []
        outside_after: list = []
        unresolved = False
        index = 0
        while index < len(parts):
            part = parts[index]
            kind = self.roles.of(part)
            if kind in valid:
                result.append(part)
                index += 1
                continue
            if is_element(part) and not has_content(part):
                changed = True
                index += 1
                continue
            if kind in CELLS:
                end = index
                while end < len(parts) and self.roles.of(parts[end]) in CELLS:
                    end += 1
                run = parts[index:end]
                index = end
                previous = result[-1] if result and self.roles.is_(result[-1], "TR") else None
                taken = self._continuing_cells(previous, run, container, columns) if previous is not None else 0
                if taken:                                    # cells on the line of the row before
                    set_kids(previous, kids(previous) + move(self.pdf, run[:taken], container, previous))
                    run = run[taken:]
                    changed = True
                if not run:
                    continue
                try:
                    rows = self.group_cells(run, container, columns)
                except CellsWithoutRows:
                    result.extend(run)
                    unresolved = True
                else:
                    result.extend(self._new_row(container, cells, container) for cells in rows)
                    changed = True
                continue
            changed = True
            index += 1
            cell = self._cell_at(part, container, result + parts[index:])
            if cell is not None:
                set_kids(cell, kids(cell) + move(self.pdf, [part], container, cell))
                continue
            at_start = not any(self.roles.of(done) in rows_kinds for done in result)
            at_end = not any(self.roles.of(rest) in rows_kinds + CELLS for rest in parts[index:])
            if is_table and (at_start or at_end):
                if (not has_caption and is_element(part)
                        and _CAPTION_TEXT.match(self.layout.text(part, container))):
                    part["/S"] = Name("/Caption")
                    has_caption = True
                    result.append(part)
                    continue
                if is_element(container.get("/P")):
                    (outside_before if at_start else outside_after).append(part)
                    continue
            result.append(self._full_width_row(container, part, container, columns))
        if not changed:
            if unresolved:
                raise CellsWithoutRows()
            return False
        set_kids(container, result)
        if outside_before or outside_after:
            parent = container["/P"]
            siblings = kids(parent)
            position = index_of(siblings, container)
            if position is None:
                siblings.append(container)
                position = len(siblings) - 1
            set_kids(parent, siblings[:position] + move(self.pdf, outside_before, container, parent)
                     + [container] + move(self.pdf, outside_after, container, parent) + siblings[position + 1:])
        return True

    def repair_row(self, row: Dictionary) -> bool:
        """Repair a TR so it holds only header and data cells."""
        columns = self.column_count(self.table_of(row))
        parts, changed = self._unwrap(row, kids(row), CELLS)
        result: list = []
        for index, part in enumerate(parts):
            if self.roles.of(part) in CELLS:
                result.append(part)
                continue
            changed = True
            if is_element(part) and not has_content(part):
                continue
            remaining = parts[index + 1:]
            cell = self._cell_at(part, row, result + remaining)
            if cell is not None:                                 # it sits inside a cell's area
                set_kids(cell, kids(cell) + move(self.pdf, [part], row, cell))
                continue
            cell_count = sum(_colspan(p) for p in result + remaining if self.roles.of(p) in CELLS)
            if columns is None or cell_count < columns:          # a cell of its own
                cell = new_element(self.pdf, "TD", row, like=row)
                set_kids(cell, move(self.pdf, [part], row, cell))
                result.append(cell)
                continue
            neighbour = next((p for p in reversed(result) if self.roles.of(p) in CELLS), None)
            if neighbour is not None:                            # the row is full: join a cell
                set_kids(neighbour, kids(neighbour) + move(self.pdf, [part], row, neighbour))
            else:
                neighbour = next(p for p in remaining if self.roles.of(p) in CELLS)
                set_kids(neighbour, move(self.pdf, [part], row, neighbour) + kids(neighbour))
        if changed:
            set_kids(row, result)
        return changed

    def repair_loose_cell(self, cell: Dictionary) -> bool:
        """A TH or TD outside a row: repair the table part it sits in."""
        parent = cell.get("/P")
        if self.roles.is_(parent, "TR"):
            return False
        if self.roles.of(parent) in ("Table",) + ROW_GROUPS:
            return self.repair_group(parent)
        grandparent = parent.get("/P") if is_element(parent) else None
        if self.roles.of(parent) in _WRAPPERS and self.roles.of(grandparent) in ("Table", "TR") + ROW_GROUPS:
            if self.roles.is_(grandparent, "TR"):
                return self.repair_row(grandparent)
            return self.repair_group(grandparent)
        raise CellsWithoutRows()
