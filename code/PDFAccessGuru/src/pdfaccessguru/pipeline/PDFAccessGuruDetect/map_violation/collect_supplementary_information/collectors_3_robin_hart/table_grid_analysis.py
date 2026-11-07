from dataclasses import dataclass, field

import pikepdf
from pikepdf import Dictionary, Name

from pdfaccessguru.exceptions.corrector_exceptions.could_not_extract_children_exception import (
    CouldNotExtractChildrenException,
)
from pdfaccessguru.model.supplementary_information.table.grid import (
    LogicalTableGrid,
    PlacedTableCell,
    SpanAdjustment,
    TableCellCorrectionPlan,
    TableCellIntersection,
    TableCellSpan,
    TableGridCoordinate,
    TableGridRow,
)
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart.utils import (
    normalize_children_of_element,
)

_RELEVANT_TABLE_STRUCTURE_TAGS = frozenset({
    pikepdf.Name("/Table"),
    pikepdf.Name("/TD"),
    pikepdf.Name("/TR"),
    pikepdf.Name("/TH"),
    pikepdf.Name("/TFoot"),
    pikepdf.Name("/TBody"),
    pikepdf.Name("/THead"),
})
_TABLE_CELL_TAGS = frozenset({Name("/TD"), Name("/TH")})
_TABLE_ROW_TAGS = frozenset({Name("/TR")})
_TABLE_SECTION_TAGS = frozenset({Name("/THead"), Name("/TBody"), Name("/TFoot"), Name("/Table")})


def _structure_children(element: pikepdf.Object) -> list[pikepdf.Object]:
    if "/K" not in element:
        return []

    children = element["/K"]
    if isinstance(children, pikepdf.Array):
        return list(children)
    if isinstance(children, pikepdf.Dictionary):
        return [children]
    return []


def _collect_table_elements(
    element: pikepdf.Object,
    mapping: dict[int, pikepdf.Object],
    next_id: list[int],
) -> None:
    if not isinstance(element, pikepdf.Dictionary):
        return

    tag = element.get("/S")
    if tag not in _RELEVANT_TABLE_STRUCTURE_TAGS:
        return

    mapping[next_id[0]] = element
    next_id[0] += 1

    for child in _structure_children(element):
        _collect_table_elements(child, mapping, next_id)


def generate_id_to_table_elements_mapping(table_element: pikepdf.Object) -> dict[int, pikepdf.Object]:
    """Map IDs to relevant table structure elements in the subtree of a /Table element."""
    mapping: dict[int, pikepdf.Object] = {}
    _collect_table_elements(table_element, mapping, [0])
    return mapping


def _collect_mcids_from_k(k: pikepdf.Object, mcids: list[int]) -> None:
    if isinstance(k, int):
        mcids.append(k)
        return

    if isinstance(k, pikepdf.Dictionary):
        if "/MCID" in k:
            mcids.append(int(k["/MCID"]))
        if k.get("/Type") == pikepdf.Name("/MCR"):
            return
        if "/K" in k:
            _collect_mcids_from_k(k["/K"], mcids)
        return

    if isinstance(k, pikepdf.Array):
        for child in k:
            _collect_mcids_from_k(child, mcids)


def find_mcids_of_element(element: pikepdf.Object) -> list[int]:
    """Collect MCIDs from a structure element and its /K subtree."""
    mcids: list[int] = []
    if not isinstance(element, pikepdf.Dictionary):
        return mcids

    if "/MCID" in element:
        mcids.append(int(element["/MCID"]))

    k = element.get("/K")
    if k is None:
        return mcids
    if isinstance(k, int):
        mcids.append(k)
        return mcids

    _collect_mcids_from_k(k, mcids)
    return mcids


@dataclass
class _MutableGridState:
    occupied_slots: dict[tuple[int, int], int] = field(default_factory=dict)


@dataclass(frozen=True)
class _CellPlacement:
    origin: TableGridCoordinate
    span: TableCellSpan
    cell_id: int
    parent_tr_id: int
    mcids: list[int]


@dataclass
class TableGridAnalysisResult:
    logical_grid: LogicalTableGrid
    correction_plans: list[TableCellCorrectionPlan]
    id_to_parent_tr_mapping: dict[int, pikepdf.Object]


def find_ancestor_table(cell: pikepdf.Object) -> pikepdf.Dictionary:
    """Walk /P until a /Table ancestor is found."""
    current = cell
    while current is not None:
        if not isinstance(current, pikepdf.Dictionary):
            break
        if current.get("/S") == Name("/Table"):
            return current
        current = current.get("/P")
    raise ValueError("No /Table ancestor found for table cell")


def collect_table_rows_in_order(table_element: pikepdf.Object) -> list[pikepdf.Dictionary]:
    """Collect /TR elements in document order from the table subtree."""
    rows: list[pikepdf.Dictionary] = []
    _collect_table_rows_recursive(table_element, rows)
    return rows


def _collect_table_rows_recursive(element: pikepdf.Object, rows: list[pikepdf.Dictionary]) -> None:
    if not isinstance(element, pikepdf.Dictionary):
        return

    tag = element.get("/S")
    if tag in _TABLE_ROW_TAGS:
        rows.append(element)
        return

    if tag not in _TABLE_SECTION_TAGS:
        return

    try:
        children = normalize_children_of_element(element)
    except CouldNotExtractChildrenException:
        return

    for child in children:
        _collect_table_rows_recursive(child, rows)


def _find_element_id(
    element: pikepdf.Object,
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
) -> int:
    for element_id, mapped_element in id_to_table_elements_mapping.items():
        if mapped_element == element:
            return element_id
    raise ValueError("Element not found in id_to_table_elements_mapping")


def find_element_id(
    element: pikepdf.Object,
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
) -> int:
    """Return the analysis ID for a table structure element."""
    return _find_element_id(element, id_to_table_elements_mapping)


def _read_table_cell_spans(cell: pikepdf.Dictionary) -> TableCellSpan:
    row_span = 1
    col_span = 1

    if "/A" not in cell:
        return TableCellSpan(row_span=row_span, col_span=col_span)

    attrs = cell["/A"]
    attr_dicts = attrs if isinstance(attrs, pikepdf.Array) else [attrs]
    for attr_dict in attr_dicts:
        if isinstance(attr_dict, Dictionary) and attr_dict.get("/O") == Name("/Table"):
            if "/RowSpan" in attr_dict:
                row_span = int(attr_dict["/RowSpan"])
            if "/ColSpan" in attr_dict:
                col_span = int(attr_dict["/ColSpan"])

    return TableCellSpan(row_span=row_span, col_span=col_span)


def _get_table_attribute_dict(cell: pikepdf.Dictionary) -> Dictionary | None:
    if "/A" not in cell:
        return None

    attrs = cell["/A"]
    attr_dicts = attrs if isinstance(attrs, pikepdf.Array) else [attrs]
    for attr_dict in attr_dicts:
        if isinstance(attr_dict, Dictionary) and attr_dict.get("/O") == Name("/Table"):
            return attr_dict
    return None


def _skip_occupied_columns(grid: _MutableGridState, start: TableGridCoordinate) -> TableGridCoordinate:
    column_index = start.column
    while (start.row, column_index) in grid.occupied_slots:
        column_index += 1
    return TableGridCoordinate(row=start.row, column=column_index)


def _cell_intersects_occupied_slots(grid: _MutableGridState, placement: _CellPlacement) -> bool:
    for row_offset in range(placement.span.row_span):
        for column_offset in range(placement.span.col_span):
            slot = (
                placement.origin.row + row_offset,
                placement.origin.column + column_offset,
            )
            if slot in grid.occupied_slots:
                return True
    return False


def _register_cell_in_grid(grid: _MutableGridState, placement: _CellPlacement) -> None:
    for row_offset in range(placement.span.row_span):
        for column_offset in range(placement.span.col_span):
            grid.occupied_slots[(
                placement.origin.row + row_offset,
                placement.origin.column + column_offset,
            )] = placement.cell_id


def _collect_conflicting_slots(
    grid: _MutableGridState,
    placement: _CellPlacement,
) -> list[TableGridCoordinate]:
    return [
        TableGridCoordinate(
            row=placement.origin.row + row_offset,
            column=placement.origin.column + column_offset,
        )
        for row_offset in range(placement.span.row_span)
        for column_offset in range(placement.span.col_span)
        if (placement.origin.row + row_offset, placement.origin.column + column_offset)
        in grid.occupied_slots
    ]


def _find_cell_origin(
    grid: _MutableGridState,
    slot: TableGridCoordinate,
    cell_id: int,
) -> TableGridCoordinate:
    origin_row = slot.row
    while origin_row > 0 and grid.occupied_slots.get((origin_row - 1, slot.column)) == cell_id:
        origin_row -= 1

    origin_column = slot.column
    while origin_column > 0 and grid.occupied_slots.get((origin_row, origin_column - 1)) == cell_id:
        origin_column -= 1

    return TableGridCoordinate(row=origin_row, column=origin_column)


def _plan_span_adjustment_for_slot(
    grid: _MutableGridState,
    slot: TableGridCoordinate,
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
    processed_blockers: set[int],
) -> SpanAdjustment | None:
    other_cell_id = grid.occupied_slots[slot.as_slot_key]
    if other_cell_id in processed_blockers:
        return None

    origin = _find_cell_origin(grid, slot, other_cell_id)
    if origin.row >= slot.row:
        return None

    blocker = id_to_table_elements_mapping[other_cell_id]
    if not isinstance(blocker, pikepdf.Dictionary):
        return None
    table_attr = _get_table_attribute_dict(blocker)
    if table_attr is None or "/RowSpan" not in table_attr:
        return None

    current_span = int(table_attr["/RowSpan"])
    new_span = slot.row - origin.row
    if new_span < 1 or new_span >= current_span:
        return None

    processed_blockers.add(other_cell_id)
    return SpanAdjustment(cell_id=other_cell_id, new_row_span=new_span)


def _plan_span_adjustments(
    grid: _MutableGridState,
    placement: _CellPlacement,
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
) -> list[SpanAdjustment]:
    conflicting_slots = _collect_conflicting_slots(grid, placement)
    if not conflicting_slots:
        return []

    adjustments: list[SpanAdjustment] = []
    processed_blockers: set[int] = set()
    for slot in conflicting_slots:
        adjustment = _plan_span_adjustment_for_slot(
            grid,
            slot,
            id_to_table_elements_mapping,
            processed_blockers,
        )
        if adjustment is not None:
            adjustments.append(adjustment)
    return adjustments


def _apply_span_adjustment_to_mutable_grid(
    grid: _MutableGridState,
    adjustment: SpanAdjustment,
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
) -> None:
    blocker = id_to_table_elements_mapping[adjustment.cell_id]
    if not isinstance(blocker, pikepdf.Dictionary):
        return
    table_attr = _get_table_attribute_dict(blocker)
    if table_attr is None or adjustment.new_row_span is None:
        return

    current_span = int(table_attr["/RowSpan"])
    new_span = adjustment.new_row_span
    if new_span >= current_span:
        return

    origin_slot = next(
        (
            TableGridCoordinate(row=row, column=column)
            for (row, column), cell_id in grid.occupied_slots.items()
            if cell_id == adjustment.cell_id
        ),
        None,
    )
    if origin_slot is None:
        return

    origin = _find_cell_origin(grid, origin_slot, adjustment.cell_id)
    blocker_span = _read_table_cell_spans(blocker)
    for row_offset in range(new_span, current_span):
        for column_offset in range(blocker_span.col_span):
            grid.occupied_slots.pop((origin.row + row_offset, origin.column + column_offset), None)


def _build_intersection(
    placement: _CellPlacement,
    grid: _MutableGridState,
) -> TableCellIntersection:
    conflicting_slots = _collect_conflicting_slots(grid, placement)
    other_cell_id = grid.occupied_slots[conflicting_slots[0].as_slot_key]
    return TableCellIntersection(
        overlapped_cell_id=placement.cell_id,
        other_cell_id=other_cell_id,
        conflicting_slots=conflicting_slots,
    )


def _plan_correction_for_intersection(
    intersection: TableCellIntersection,
    placement: _CellPlacement,
    grid: _MutableGridState,
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
) -> TableCellCorrectionPlan | None:
    if placement.mcids:
        adjustments = _plan_span_adjustments(grid, placement, id_to_table_elements_mapping)
        if not adjustments:
            return None
        for adjustment in adjustments:
            _apply_span_adjustment_to_mutable_grid(grid, adjustment, id_to_table_elements_mapping)
        return TableCellCorrectionPlan(
            intersection=intersection,
            span_adjustment=adjustments[0],
        )

    return TableCellCorrectionPlan(
        intersection=intersection,
        cell_to_remove_id=placement.cell_id,
    )


def analyze_table_grid(
    table_element: pikepdf.Object,
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
    affected_cell_id: int,
) -> TableGridAnalysisResult:
    """Build the logical grid and plan a correction for the affected cell only."""
    rows = collect_table_rows_in_order(table_element)
    if not rows:
        raise ValueError("Table has no rows")

    logical_grid = LogicalTableGrid()
    mutable_grid = _MutableGridState()
    id_to_parent_tr_mapping: dict[int, pikepdf.Object] = {}
    correction_plans: list[TableCellCorrectionPlan] = []

    for row_index, row in enumerate(rows):
        row_id = _find_element_id(row, id_to_table_elements_mapping)
        logical_grid.rows.append(TableGridRow(index=row_index, element_id=row_id))

        if "/K" not in row:
            continue

        try:
            cells = normalize_children_of_element(row)
        except CouldNotExtractChildrenException:
            continue

        column_index = 0
        for cell in cells:
            if not isinstance(cell, pikepdf.Dictionary):
                continue
            if cell.get("/S") not in _TABLE_CELL_TAGS:
                continue

            column_index = _skip_occupied_columns(
                mutable_grid,
                TableGridCoordinate(row=row_index, column=column_index),
            ).column

            cell_id = _find_element_id(cell, id_to_table_elements_mapping)
            span = _read_table_cell_spans(cell)
            mcids = find_mcids_of_element(cell)
            id_to_parent_tr_mapping[cell_id] = row

            placement = _CellPlacement(
                origin=TableGridCoordinate(row=row_index, column=column_index),
                span=span,
                cell_id=cell_id,
                parent_tr_id=row_id,
                mcids=mcids,
            )

            if _cell_intersects_occupied_slots(mutable_grid, placement):
                intersection = _build_intersection(placement, mutable_grid)
                involves_affected = (
                    placement.cell_id == affected_cell_id
                    or intersection.other_cell_id == affected_cell_id
                )
                if involves_affected:
                    plan = _plan_correction_for_intersection(
                        intersection,
                        placement,
                        mutable_grid,
                        id_to_table_elements_mapping,
                    )
                    if plan is not None:
                        correction_plans.append(plan)
                        if plan.span_adjustment is not None:
                            placed_cell = PlacedTableCell(
                                element_id=placement.cell_id,
                                origin=placement.origin,
                                span=placement.span,
                                parent_tr_id=row_id,
                                mcids=mcids,
                            )
                            logical_grid.cells.append(placed_cell)
                            _register_cell_in_grid(mutable_grid, placement)
                            logical_grid.slot_to_cell_id.update({
                                (
                                    placement.origin.row + row_offset,
                                    placement.origin.column + column_offset,
                                ): placement.cell_id
                                for row_offset in range(span.row_span)
                                for column_offset in range(span.col_span)
                            })
                column_index += span.col_span
                continue

            placed_cell = PlacedTableCell(
                element_id=cell_id,
                origin=placement.origin,
                span=placement.span,
                parent_tr_id=row_id,
                mcids=mcids,
            )
            logical_grid.cells.append(placed_cell)
            _register_cell_in_grid(mutable_grid, placement)
            logical_grid.slot_to_cell_id.update({
                (
                    placement.origin.row + row_offset,
                    placement.origin.column + column_offset,
                ): cell_id
                for row_offset in range(span.row_span)
                for column_offset in range(span.col_span)
            })

            column_index += span.col_span

    return TableGridAnalysisResult(
        logical_grid=logical_grid,
        correction_plans=correction_plans,
        id_to_parent_tr_mapping=id_to_parent_tr_mapping,
    )
