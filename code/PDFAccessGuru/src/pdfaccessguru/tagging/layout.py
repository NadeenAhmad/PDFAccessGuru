"""
Reading a page like a person (Phase 6): which text is a heading (and which level), a paragraph,
a list item, a caption, a header or footer; where the pictures are; and the reading order,
also on pages with two columns. Uses only PyMuPDF's text and image positions.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

import pymupdf as fitz

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.pictures import CAPTION_START
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.lists import looks_like_marker

_NUMBERED_HEADING = re.compile(r"^\s*((?:\d+|[A-Z])(?:\.\d+)*)\.?\s+\S")
_PAGE_NUMBER = re.compile(r"^\s*(?:page|seite)?\s*(\d+|[ivxlcdm]+)(\s*(/|of|von)\s*\d+)?\s*$", re.IGNORECASE)
_TABLE_CAPTION = re.compile(r"^\s*(table|tab\.|tabelle)\s*\d", re.IGNORECASE)


@dataclass
class Line:
    rect: fitz.Rect
    text: str
    size: float
    bold: bool


@dataclass
class Item:
    kind: str                     # H, P, LI, Figure, Caption, Artifact, Decoration, Table, Cell
    page: int
    rect: fitz.Rect
    lines: list[Line] = field(default_factory=list)
    level: int = 0                # heading level 1-6
    text: str = ""
    table: int = -1               # cells: which table, row and column; header row; column span
    row: int = -1
    col: int = -1
    header: bool = False
    col_span: int = 1
    row_span: int = 1

    def contains(self, point: fitz.Point, margin: float = 2.0) -> bool:
        if self.kind in ("Figure", "Cell"):
            area = fitz.Rect(self.rect)
            area.x0 -= margin; area.y0 -= margin; area.x1 += margin; area.y1 += margin
            return area.contains(point)
        for line in self.lines:
            height = max(line.rect.height, 4)
            area = fitz.Rect(line.rect.x0 - margin, line.rect.y0 - height * 0.5,
                             line.rect.x1 + margin, line.rect.y1 + height * 0.5)
            if area.contains(point):
                return True
        return False


def _lines_of(block: dict) -> list[Line]:
    lines = []
    for line in block.get("lines", []):
        spans = [span for span in line["spans"] if span["text"].strip()]
        if not spans:
            continue
        text = " ".join(" ".join(span["text"].split()) for span in spans).strip()
        chars = sum(len(span["text"].strip()) for span in spans)
        size = sum(span["size"] * len(span["text"].strip()) for span in spans) / max(chars, 1)
        bold_chars = sum(len(span["text"].strip()) for span in spans
                         if span["flags"] & 16 or "bold" in span["font"].lower() or "black" in span["font"].lower())
        lines.append(Line(fitz.Rect(line["bbox"]), text, round(size, 1), bold_chars > chars * 0.6))
    return lines


def _normalized(text: str) -> str:
    return re.sub(r"\d+", "#", text.lower()).strip()


def analyse(document: fitz.Document) -> list[list[Item]]:
    """Items of every page, in reading order."""
    pages = [document[index].get_text("dict") for index in range(document.page_count)]
    sizes: Counter = Counter()
    for data in pages:
        for block in data["blocks"]:
            for line in _lines_of(block):
                sizes[line.size] += len(line.text)
    body = sizes.most_common(1)[0][0] if sizes else 10.0

    # Headers and footers: short lines near the top or bottom that repeat on many pages, and page numbers.
    margins: Counter = Counter()
    for index, data in enumerate(pages):
        height = document[index].rect.height
        for block in data["blocks"]:
            for line in _lines_of(block):
                if line.rect.y1 < height * 0.09 or line.rect.y0 > height * 0.91:
                    margins[_normalized(line.text)] += 1
    # (a two-page handout counts: the line must be on both pages)
    repeated = {text for text, count in margins.items() if count >= max(2, document.page_count * 0.4)}

    # Images repeated at the same place in the header or footer of several pages (logos)
    repeated_images: Counter = Counter()
    for index, data in enumerate(pages):
        height = document[index].rect.height
        for block in data["blocks"]:
            if block["type"] == 1:
                rect = fitz.Rect(block["bbox"])
                if rect.y1 < height * 0.15 or rect.y0 > height * 0.85:
                    repeated_images[tuple(round(v / 4) for v in rect)] += 1
    repeated_logos = {key for key, count in repeated_images.items() if count >= max(3, document.page_count * 0.4)}

    result: list[list[Item]] = []
    heading_sizes: set[float] = set()
    for index, data in enumerate(pages):
        page = document[index]
        height = page.rect.height
        items: list[Item] = []
        tables = _tables(page, index)
        table_areas = [item.rect for item in tables if item.kind == "Table"]
        for block in data["blocks"]:
            if block["type"] == 1:
                rect = fitz.Rect(block["bbox"])
                if rect.width > 4 and rect.height > 4:
                    decorative = is_decoration(rect, page.rect) or \
                        tuple(round(v / 4) for v in rect) in repeated_logos
                    items.append(Item("Decoration" if decorative else "Figure", index, rect))
                continue
            lines = [line for line in _lines_of(block)
                     if not any(area.contains(fitz.Point((line.rect.x0 + line.rect.x1) / 2,
                                                         (line.rect.y0 + line.rect.y1) / 2)) for area in table_areas)]
            if not lines:
                continue
            current: Item | None = None
            for line in lines:
                in_margin = line.rect.y1 < height * 0.09 or line.rect.y0 > height * 0.91
                page_number = _PAGE_NUMBER.match(line.text) and (line.rect.y1 < height * 0.12 or line.rect.y0 > height * 0.85)
                if page_number or (in_margin and _normalized(line.text) in repeated):
                    items.append(Item("Artifact", index, fitz.Rect(line.rect), [line], text=line.text))
                    current = None
                    continue
                looks_like_heading = line.size >= body * 1.12 or (line.bold and len(lines) == 1)
                starts_item = looks_like_marker(line.text) and len(line.text) > 3 and not looks_like_heading
                if current is None or (starts_item and current.kind in ("P", "LI")) or \
                        (current.kind == "LI" and line.rect.x0 < current.lines[0].rect.x0 - 3):
                    current = Item("LI" if starts_item else "P", index, fitz.Rect(line.rect), [line])
                    items.append(current)
                else:
                    current.lines.append(line)
                    current.rect |= line.rect
        # merge list-item continuation blocks (indented text right below an item, no marker)
        merged: list[Item] = []
        for item in items:
            previous = merged[-1] if merged else None
            if (previous is not None and previous.kind == "LI" and item.kind == "P"
                    and item.rect.y0 - previous.rect.y1 < previous.lines[-1].rect.height * 0.8
                    and item.rect.x0 > previous.rect.x0 + 3):
                previous.lines.extend(item.lines)
                previous.rect |= item.rect
                continue
            merged.append(item)
        for item in merged:
            item.text = " ".join(line.text for line in item.lines)
            if item.kind == "P":
                _classify_text(item, body, heading_sizes)
        # a heading written over two lines (two blocks) is one heading
        joined: list[Item] = []
        for item in merged:
            previous = joined[-1] if joined else None
            if (previous is not None and previous.kind == item.kind == "H"
                    and abs(max(l.size for l in previous.lines) - max(l.size for l in item.lines)) < 0.5
                    and 0 <= item.rect.y0 - previous.rect.y1 < previous.lines[-1].rect.height * 1.2):
                previous.lines.extend(item.lines)
                previous.rect |= item.rect
                previous.text += " " + item.text
                continue
            joined.append(item)
        result.append(_reading_order(joined + [item for item in tables if item.kind == "Table"], page.rect,
                                     [item for item in tables if item.kind == "Cell"]))

    _set_heading_levels([item for items in result for item in items if item.kind == "H"], heading_sizes)
    return result


def _set_heading_levels(headings: list[Item], heading_sizes) -> None:
    """
    Numbered headings get their numbering depth ("2 Methods" -> 1, "2.3.1 Data" -> 3). A larger,
    unnumbered heading (the document title) is level 1 and moves the numbered ones one level down.
    Other unnumbered headings ("Abstract") take the level of numbered headings of the same size;
    without numbered headings, levels follow the size.
    """
    def size_of(item: Item) -> float:
        return max(line.size for line in item.lines)

    depth_sizes: dict[int, list[float]] = {}
    for item in headings:
        numbered = _NUMBERED_HEADING.match(item.text)
        if numbered:
            depth_sizes.setdefault(numbered.group(1).count(".") + 1, []).append(size_of(item))
    if not depth_sizes:
        ranked = sorted(heading_sizes, reverse=True)
        for item in headings:
            size = size_of(item)
            item.level = min(6, ranked.index(size) + 1) if size in ranked else 2
        return
    typical = {depth: sorted(sizes)[len(sizes) // 2] for depth, sizes in depth_sizes.items()}
    top = typical[min(typical)]
    shift = 1 if any(not _NUMBERED_HEADING.match(item.text) and size_of(item) > top + 0.5 for item in headings) else 0
    for item in headings:
        numbered = _NUMBERED_HEADING.match(item.text)
        size = size_of(item)
        if numbered:
            item.level = min(6, numbered.group(1).count(".") + 1 + shift)
        elif size > top + 0.5:
            item.level = 1                                  # the title above the numbered sections
        else:                                              # same size as a numbered level, else the next one down
            depth = min(typical, key=lambda d: (abs(typical[d] - size), d))
            item.level = min(6, depth + shift if abs(typical[depth] - size) <= 0.5 else
                             max(typical) + 1 + shift if size < min(typical.values()) else depth + shift)


def is_decoration(rect: fitz.Rect, page_rect: fitz.Rect) -> bool:
    """Lines, dots, stripes and page backgrounds: drawn for looks, not content."""
    short, long = sorted((rect.width, rect.height))
    if short < 12:
        return True                                        # a thin line or a tiny dot
    if long / short > 12:
        return True                                        # a stripe or bar
    return abs(rect & page_rect) > abs(page_rect) * 0.6    # a page background


def _classify_text(item: Item, body: float, heading_sizes: set[float]) -> None:
    text = item.text
    size = max(line.size for line in item.lines)
    short = len(item.lines) <= 3 and len(text) <= 200
    if CAPTION_START.match(text) or _TABLE_CAPTION.match(text):
        item.kind = "Caption"
        return
    looks_like_sentence_end = text.rstrip().endswith((".", ":", ";", ","))
    bigger = size >= body * 1.12
    bold_heading = all(line.bold for line in item.lines) and size >= body * 0.95 and len(text) <= 120 \
        and not looks_like_sentence_end
    if short and (bigger or bold_heading) and any(ch.isalpha() for ch in text):
        item.kind = "H"
        heading_sizes.add(size)


def _tables(page: fitz.Page, page_index: int) -> list[Item]:
    """Tables PyMuPDF finds from their ruling lines: a Table item, then its cells row by row."""
    found: list[Item] = []
    try:
        tables = page.find_tables().tables
    except Exception:
        return found
    for number, table in enumerate(tables):
        if table.row_count < 2 or table.col_count < 2:
            continue
        header_row = 0 if table.header is not None and not table.header.external else -1
        rows = table.rows
        # Where each row and column starts; a merged cell covers every row/column that starts
        # inside it (a column without any cell of its own is always covered from the left).
        row_tops = [row.bbox[1] for row in rows]
        col_lefts: list[float] = []
        for col_index in range(table.col_count):
            lefts = [row.cells[col_index][0] for row in rows
                     if col_index < len(row.cells) and row.cells[col_index] is not None]
            col_lefts.append(min(lefts) if lefts else (col_lefts[-1] + 1 if col_lefts else 0))
        cells: list[Item] = []
        for row_index, row in enumerate(rows):
            for col_index, cell in enumerate(row.cells):
                if cell is None:                       # part of a merged cell to the left or above
                    continue
                x1, y1 = cell[2], cell[3]
                cells.append(Item("Cell", page_index, fitz.Rect(cell), table=number, row=row_index, col=col_index,
                                  header=row_index == header_row,
                                  col_span=1 + sum(1 for left in col_lefts[col_index + 1:] if left < x1 - 1),
                                  row_span=1 + sum(1 for top in row_tops[row_index + 1:] if top < y1 - 1)))
        if _is_regular(cells, len(rows), table.col_count):
            found.append(Item("Table", page_index, fitz.Rect(table.bbox), table=number))
            found += cells
        # otherwise (overlapping or missing cells) the text stays as paragraphs: a broken
        # table is worse for a screen reader than plain text
    return found


def _is_regular(cells: list[Item], row_count: int, col_count: int) -> bool:
    """Every place of the grid is covered by exactly one cell."""
    covered = [[0] * col_count for _ in range(row_count)]
    for cell in cells:
        for row in range(cell.row, cell.row + cell.row_span):
            for col in range(cell.col, cell.col + cell.col_span):
                if row >= row_count or col >= col_count:
                    return False
                covered[row][col] += 1
    return all(count == 1 for row in covered for count in row)


def _reading_order(items: list[Item], page_rect: fitz.Rect, cells: list[Item] | None = None) -> list[Item]:
    """Top to bottom; on pages with two columns, the left column before the right one. Table
    cells follow their table, row by row."""
    ordered_items = _order(items, page_rect)
    if not cells:
        return ordered_items
    result: list[Item] = []
    for item in ordered_items:
        result.append(item)
        if item.kind == "Table":
            result += [cell for cell in cells if cell.table == item.table]
    return result


def _order(items: list[Item], page_rect: fitz.Rect) -> list[Item]:
    content = [item for item in items if item.kind not in ("Artifact", "Decoration")]
    if not content:
        return items
    left_edge = min(item.rect.x0 for item in content)
    right_edge = max(item.rect.x1 for item in content)
    middle = (left_edge + right_edge) / 2
    width = right_edge - left_edge
    narrow = [item for item in content if item.rect.width < width * 0.55]
    left = [item for item in narrow if item.rect.x1 <= middle + 5]
    right = [item for item in narrow if item.rect.x0 >= middle - 5]
    two_columns = len(left) >= 2 and len(right) >= 2 and sum(len(i.text) for i in left + right) > \
        0.5 * sum(len(i.text) for i in content)
    if not two_columns:
        ordered = sorted(content, key=lambda item: (round(item.rect.y0 / 3), item.rect.x0))
    else:
        # full-width items split the page into bands; in each band, left column then right column
        wide = sorted((item for item in content if item not in left and item not in right),
                      key=lambda item: item.rect.y0)
        ordered, top = [], -1.0
        for separator in wide + [None]:
            bottom = separator.rect.y0 if separator is not None else float("inf")
            band = [item for item in left + right if top <= item.rect.y0 < bottom]
            ordered += sorted((i for i in band if i in left), key=lambda i: i.rect.y0)
            ordered += sorted((i for i in band if i in right), key=lambda i: i.rect.y0)
            if separator is not None:
                ordered.append(separator)
                top = separator.rect.y0
    artifacts = [item for item in items if item.kind in ("Artifact", "Decoration")]
    return ordered + artifacts
