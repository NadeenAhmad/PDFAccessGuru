import json
from dataclasses import dataclass

from pikepdf import Array, Dictionary, Integer, Name, Pdf

from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_review


_ROW_CONTAINERS = frozenset(
    {Name("/Table"), Name("/THead"), Name("/TBody"), Name("/TFoot")}
)
_CELL_TAGS = frozenset({Name("/TH"), Name("/TD")})
_MAX_TABLE_ROWS = 1000
_MAX_TABLE_COLUMNS = 1000
_MAX_TABLE_CELLS = 5000
_MAX_GRID_SLOTS = 100000
_MAX_TABLE_JSON_LENGTH = 500000


@dataclass
class _Cell:
    """A table cell together with its calculated position in the logical grid."""

    cell_id: str
    element: Dictionary
    tag: str
    row: int
    column: int
    row_span: int
    column_span: int
    text: str | None


@dataclass
class _TableModel:
    """The logical table grid and the calculated width of each explicit row."""

    row_count: int
    row_widths: list[int]
    cells: list[_Cell]
    occupied: dict[tuple[int, int], _Cell]


@corrector("table-rows-span-different-number-columns")
def correct_table_rows_span_different_number_columns(
    detected_violation: DetectedViolation,
    pdf: Pdf,
) -> None:
    """
    Correct veraPDF rule 7.2-42.

    The LLM receives the complete logical table and chooses the intended number
    of columns. Grid construction, response validation and the PDF modification
    are deterministic. Only /ColSpan values on cells at a row's right boundary
    are changed, so existing cells and their content are never removed.
    """
    # Resolve custom structure tags before validating and reading the table.
    table = detected_violation.affected_element
    role_map = _get_role_map(pdf)
    if (
        not isinstance(table, Dictionary)
        or _resolve_role(table.get("/S"), role_map) != Name("/Table")
    ):
        raise _correction_error(detected_violation, "affected element is not a /Table")

    model = _build_table_model(table, detected_violation, role_map)
    # A table that is already rectangular needs neither an LLM call nor a change.
    if len(set(model.row_widths)) <= 1:
        return

    # The LLM receives structure and content context, but never edits the PDF itself.
    table_json = _render_table_json(model)
    if len(table_json) > _MAX_TABLE_JSON_LENGTH:
        raise _correction_error(
            detected_violation, "table representation is too large for the LLM"
        )

    correct_column_count = determine_correct_column_count(table_json)
    # Only validated, deterministic span changes are considered for application.
    _validate_column_count(correct_column_count, model, detected_violation)
    span_changes = _plan_column_span_changes(
        model, correct_column_count, detected_violation
    )

    # Simulate every change before touching the PDF. This catches interactions
    # with RowSpan cells and guarantees that failed corrections remain atomic.
    span_overrides = {
        cell.cell_id: column_span
        for cell, column_span in span_changes.values()
    }
    corrected_model = _build_table_model(
        table, detected_violation, role_map, span_overrides
    )
    if not corrected_model.row_widths or any(
        width != correct_column_count for width in corrected_model.row_widths
    ):
        raise _correction_error(detected_violation, "could not create a rectangular table grid")
    for cell, column_span in span_changes.values():
        _write_column_span(cell.element, column_span)


def determine_correct_column_count(table_json: str) -> int:
    """Ask the LLM which represented column count is semantically correct."""
    provider = OpenRouterBaseProvider()
    system_prompt, user_prompt = build_prompt_determine_correct_column_count(table_json)
    response = provider.send_message(system_prompt, user_prompt, json_mode=True)

    try:
        parsed = json.loads(response)
        column_count = parsed["correct_column_count"]
    except (json.JSONDecodeError, KeyError, TypeError) as exception:
        raise CouldNotCorrectDetectedViolationException(
            "table-rows-span-different-number-columns: invalid LLM response"
        ) from exception

    # bool is a subclass of int and must not be accepted as a column count.
    if isinstance(column_count, bool) or not isinstance(column_count, int):
        raise CouldNotCorrectDetectedViolationException(
            "table-rows-span-different-number-columns: "
            "LLM column count is not an integer"
        )
    return column_count


def build_prompt_determine_correct_column_count(table_json: str) -> tuple[str, str]:
    """Build the prompts while keeping untrusted table data in the user role."""
    system_prompt = """You repair logical PDF/UA table structures.
You receive a JSON representation of one complete table. Cells contain their tag,
zero-based origin, RowSpan, ColSpan, and any available accessible text. row_widths
lists how many logical columns each explicit PDF /TR row currently spans.

Determine the intended total column count from the repeated row structure, headers,
cell contents, spans, and observed row widths. Choose exactly one value already
present in `candidate_column_counts`; do not invent a new count. Usually a single
outlying ColSpan is erroneous and the consistent majority is correct, but use the
table semantics when they provide stronger evidence.

Return only a JSON object of this exact form:
{"correct_column_count": <integer>}"""
    user_prompt = f"Complete logical table:\n{table_json}"
    return system_prompt, user_prompt


def _build_table_model(
    table: Dictionary,
    detected_violation: DetectedViolation,
    role_map: Dictionary | None = None,
    column_span_overrides: dict[str, int] | None = None,
) -> _TableModel:
    """Read the structure tree and place all cells in a logical table grid."""
    rows: list[Dictionary] = []
    _collect_rows(table, rows, role_map)
    if not rows or len(rows) > _MAX_TABLE_ROWS:
        raise _correction_error(
            detected_violation, "table has no usable rows or is too large"
        )

    occupied: dict[tuple[int, int], _Cell] = {}
    cells: list[_Cell] = []
    occupied_slot_count = 0

    # RowSpan cells reserve slots in following rows. Each new cell is therefore
    # placed in the first contiguous block that is still free in its source row.
    for row_index, row in enumerate(rows):
        column = 0
        for element in _children(row):
            if (
                not isinstance(element, Dictionary)
                or _resolve_role(element.get("/S"), role_map) not in _CELL_TAGS
            ):
                continue

            cell_id = f"cell-{len(cells) + 1}"
            row_span, column_span = _read_spans(element, detected_violation)
            if column_span_overrides is not None:
                column_span = column_span_overrides.get(cell_id, column_span)
            while not _block_is_free(occupied, row_index, column, column_span):
                column += 1
                if column + column_span > _MAX_TABLE_COLUMNS:
                    raise _correction_error(
                        detected_violation, "table has too many logical columns"
                    )

            if len(cells) >= _MAX_TABLE_CELLS:
                raise _correction_error(detected_violation, "table has too many cells")
            occupied_slot_count += row_span * column_span
            if occupied_slot_count > _MAX_GRID_SLOTS:
                raise _correction_error(
                    detected_violation, "logical table grid is too large"
                )

            cell = _Cell(
                cell_id=cell_id,
                element=element,
                tag=str(_resolve_role(element.get("/S"), role_map)),
                row=row_index,
                column=column,
                row_span=row_span,
                column_span=column_span,
                text=_accessible_text(element),
            )
            cells.append(cell)
            for row_offset in range(row_span):
                for column_offset in range(column_span):
                    occupied[(row_index + row_offset, column + column_offset)] = cell
            column += column_span

    if not cells:
        raise _correction_error(detected_violation, "table contains no /TH or /TD cells")

    # The last occupied column determines the logical width of each explicit row.
    row_widths: list[int] = []
    for row_index in range(len(rows)):
        occupied_columns = [
            column
            for occupied_row, column in occupied
            if occupied_row == row_index
        ]
        if not occupied_columns:
            raise _correction_error(detected_violation, "table contains an empty row")
        row_widths.append(max(occupied_columns) + 1)

    return _TableModel(
        row_count=len(rows),
        row_widths=row_widths,
        cells=cells,
        occupied=occupied,
    )


def _collect_rows(
    element: Dictionary,
    rows: list[Dictionary],
    role_map: Dictionary | None,
) -> None:
    """Collect all /TR elements below the table and its sections in order."""
    tag = _resolve_role(element.get("/S"), role_map)
    if tag == Name("/TR"):
        rows.append(element)
        return
    if tag not in _ROW_CONTAINERS:
        return
    for child in _children(element):
        if isinstance(child, Dictionary):
            _collect_rows(child, rows, role_map)


def _get_role_map(pdf: Pdf) -> Dictionary | None:
    """Return the document RoleMap used for custom structure element names."""
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(structure_tree_root, Dictionary):
        return None
    role_map = structure_tree_root.get("/RoleMap")
    return role_map if isinstance(role_map, Dictionary) else None


def _resolve_role(role: object, role_map: Dictionary | None) -> object:
    """Resolve custom structure types, including chained RoleMap entries."""
    if role_map is None:
        return role

    current = role
    visited: set[str] = set()
    while isinstance(current, Name):
        role_name = str(current)
        if role_name in visited or role_name not in role_map:
            break
        visited.add(role_name)
        mapped_role = role_map.get(role_name)
        if not isinstance(mapped_role, Name):
            break
        current = mapped_role
    return current


def _children(element: Dictionary) -> list:
    """Normalize dictionary and array-valued /K entries to a child list."""
    children = element.get("/K")
    if isinstance(children, Array):
        return list(children)
    if isinstance(children, Dictionary):
        return [children]
    return []


def _element_identity(element: Dictionary) -> tuple[int, int] | int:
    """Return a stable key for indirect and direct pikepdf dictionaries."""
    objgen = getattr(element, "objgen", (0, 0))
    return objgen if objgen != (0, 0) else id(element)


def _read_spans(
    cell: Dictionary,
    detected_violation: DetectedViolation,
) -> tuple[int, int]:
    """Read and validate a cell's /RowSpan and /ColSpan, defaulting both to one."""
    row_span = 1
    column_span = 1
    attributes = _table_attributes(cell)
    if attributes is not None:
        try:
            row_span = int(str(attributes.get("/RowSpan", 1)))
            column_span = int(str(attributes.get("/ColSpan", 1)))
        except (TypeError, ValueError, OverflowError) as exception:
            raise _correction_error(detected_violation, "invalid table cell span") from exception
    if (
        row_span < 1
        or column_span < 1
        or row_span > _MAX_TABLE_ROWS
        or column_span > _MAX_TABLE_COLUMNS
    ):
        raise _correction_error(
            detected_violation, "table cell span is outside the supported range"
        )
    return row_span, column_span


def _attribute_dictionaries(cell: Dictionary) -> list[Dictionary]:
    """Return all dictionary entries from a cell's /A attribute value."""
    attributes = cell.get("/A")
    if isinstance(attributes, Dictionary):
        return [attributes]
    if isinstance(attributes, Array):
        return [item for item in attributes if isinstance(item, Dictionary)]
    return []


def _table_attributes(cell: Dictionary) -> Dictionary | None:
    """Return the effective (last) table-owner attribute dictionary."""
    return next(
        (
            attributes
            for attributes in reversed(_attribute_dictionaries(cell))
            if attributes.get("/O") == Name("/Table")
        ),
        None,
    )


def _block_is_free(
    occupied: dict[tuple[int, int], _Cell],
    row: int,
    column: int,
    width: int,
) -> bool:
    """Check whether consecutive grid columns are free in the given row."""
    return all(
        (row, candidate) not in occupied
        for candidate in range(column, column + width)
    )


def _accessible_text(element: Dictionary) -> str | None:
    """Collect accessible replacement or description text from a cell subtree."""
    values: list[str] = []
    visited: set[tuple[int, int] | int] = set()

    def collect(current: Dictionary) -> None:
        """Recursively collect text while protecting against malformed cycles."""
        identity = _element_identity(current)
        if identity in visited:
            return
        visited.add(identity)

        for key in ("/ActualText", "/Alt", "/E", "/T"):
            value = current.get(key)
            if value is not None and str(value).strip():
                values.append(str(value).strip())
        for child in _children(current):
            if isinstance(child, Dictionary):
                collect(child)

    collect(element)
    return " ".join(dict.fromkeys(values))[:1000] or None


def _render_table_json(model: _TableModel) -> str:
    """Serialize the logical table and column-count candidates for the LLM."""
    candidate_column_counts = sorted(set(model.row_widths))
    serializable = {
        "explicit_tr_count": model.row_count,
        "row_widths": model.row_widths,
        "candidate_column_counts": candidate_column_counts,
        "cells": [
            {
                "id": cell.cell_id,
                "tag": cell.tag,
                "row": cell.row,
                "column": cell.column,
                "row_span": cell.row_span,
                "column_span": cell.column_span,
                "accessible_text": cell.text,
            }
            for cell in model.cells
        ],
    }
    return json.dumps(serializable, ensure_ascii=False, separators=(",", ":"))


def _validate_column_count(
    column_count: int,
    model: _TableModel,
    detected_violation: DetectedViolation,
) -> None:
    """Reject an LLM choice that is not an observed, supported row width."""
    if (
        column_count not in set(model.row_widths)
        or column_count < 1
        or column_count > _MAX_TABLE_COLUMNS
    ):
        raise _correction_error(
            detected_violation, "LLM selected an unsupported column count"
        )


def _plan_column_span_changes(
    model: _TableModel,
    target: int,
    detected_violation: DetectedViolation,
) -> dict[str, tuple[_Cell, int]]:
    """Calculate safe /ColSpan changes without modifying the PDF."""
    requested_spans: dict[str, tuple[_Cell, int]] = {}

    for row, width in enumerate(model.row_widths):
        if width == target:
            continue

        # Short rows extend their rightmost cell. Wide rows may only be shortened
        # when the target boundary cuts through an existing spanning cell.
        boundary_column = target - 1 if width > target else width - 1
        cell = model.occupied.get((row, boundary_column))
        if cell is None:
            raise _correction_error(detected_violation, "row contains a structural gap")

        new_span = target - cell.column
        if new_span < 1:
            raise _correction_error(detected_violation, "column count would remove table content")
        if width > target and cell.column + cell.column_span <= target:
            raise _correction_error(
                detected_violation, "column count would remove complete table cells"
            )

        previous = requested_spans.get(cell.cell_id)
        if previous is not None and previous[1] != new_span:
            raise _correction_error(detected_violation, "conflicting span changes are required")
        requested_spans[cell.cell_id] = (cell, new_span)

    if not requested_spans:
        raise _correction_error(detected_violation, "LLM choice does not require a correction")
    return requested_spans


def _write_column_span(cell: Dictionary, column_span: int) -> None:
    """Write /ColSpan while preserving existing non-table cell attributes."""
    table_attributes = _table_attributes(cell)
    if table_attributes is None:
        # Keep layout attributes intact by adding a separate table-owner dictionary.
        table_attributes = Dictionary({"/O": Name("/Table")})
        current_attributes = cell.get("/A")
        if isinstance(current_attributes, Array):
            current_attributes.append(table_attributes)
        elif isinstance(current_attributes, Dictionary):
            cell["/A"] = Array([current_attributes, table_attributes])
        else:
            cell["/A"] = table_attributes

    if column_span == 1:
        if "/ColSpan" in table_attributes:
            del table_attributes["/ColSpan"]
    else:
        table_attributes["/ColSpan"] = Integer(column_span)
        report_review("A table cell column span was changed based on a language model decision. Please check the table.")


def _correction_error(
    detected_violation: DetectedViolation,
    reason: str,
) -> CouldNotCorrectDetectedViolationException:
    """Create a correction exception containing the violation name and reason."""
    return CouldNotCorrectDetectedViolationException(
        f"{detected_violation.violation.name}: {reason}"
    )
