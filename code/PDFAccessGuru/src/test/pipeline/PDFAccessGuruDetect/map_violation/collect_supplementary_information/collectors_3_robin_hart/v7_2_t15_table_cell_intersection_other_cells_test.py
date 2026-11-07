import pikepdf
import pytest
from pikepdf import Array, Dictionary, Integer, Name

from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.model.supplementary_information.table.grid import TableGridCoordinate
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collectors_3_robin_hart.table_grid_analysis import (
    analyze_table_grid,
    collect_table_rows_in_order,
    find_ancestor_table,
    generate_id_to_table_elements_mapping,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collectors_3_robin_hart.v7_2_t15_table_cell_intersection_other_cells import (
    collect_supplementary_information_7_2_t15,
)


def _make_table_attr(*, row_span: int | None = None, col_span: int | None = None) -> Dictionary:
    attr = Dictionary({"/O": Name("/Table")})
    if row_span is not None:
        attr["/RowSpan"] = Integer(row_span)
    if col_span is not None:
        attr["/ColSpan"] = Integer(col_span)
    return attr


def _make_content_child(*, mcid: int | None = None) -> Dictionary:
    child = Dictionary({"/S": Name("/Span")})
    if mcid is not None:
        child["/MCID"] = Integer(mcid)
    return child


def _make_cell(
    *,
    cell_type: str = "/TD",
    row_span: int | None = None,
    col_span: int | None = None,
    content: list | None = None,
    attrs_as_array: bool = False,
    marker: str | None = None,
) -> Dictionary:
    cell_dict: dict = {"/S": Name(cell_type)}
    if marker is not None:
        cell_dict["/Alt"] = marker
    if row_span is not None or col_span is not None:
        table_attr = _make_table_attr(row_span=row_span, col_span=col_span)
        cell_dict["/A"] = Array([table_attr]) if attrs_as_array else table_attr
    if content is not None:
        cell_dict["/K"] = Array(content)
    return Dictionary(cell_dict)


def _make_row(*cells: Dictionary) -> Dictionary:
    return Dictionary({"/S": Name("/TR"), "/K": Array(cells)})


def _make_table(*rows: Dictionary) -> Dictionary:
    return Dictionary({"/S": Name("/Table"), "/K": Array(rows)})


def _wire_table_parents(table: Dictionary) -> None:
    for row in table["/K"]:
        row["/P"] = table
        for cell in row["/K"]:
            cell["/P"] = row


def _find_cell_id(mapping: dict[int, pikepdf.Object], marker: str) -> int:
    for element_id, element in mapping.items():
        if element.get("/Alt") == marker:
            return element_id
    raise AssertionError(f"Cell with marker {marker!r} not found")


def test_collect_supplementary_information_7_2_t15_empty_overlapped_cell_is_removed():
    """
    Table layout:
        Row 0: [TD A] [TD B] [TD C (RowSpan=2)]
        Row 1: [TD D (ColSpan=3, empty)]  <- overlaps slot (1,2); affected cell

    The empty overlapped cell has no MCIDs, so the collector plans its removal.
    """
    cell_a = _make_cell(marker="A")
    cell_b = _make_cell(marker="B")
    cell_c = _make_cell(marker="C", row_span=2)
    cell_d = _make_cell(marker="D", col_span=3)
    table = _make_table(_make_row(cell_a, cell_b, cell_c), _make_row(cell_d))
    _wire_table_parents(table)

    id_mapping = generate_id_to_table_elements_mapping(table)
    affected_cell_id = _find_cell_id(id_mapping, "D")

    supplementary_information = collect_supplementary_information_7_2_t15(
        VeraPdfViolation(
            rule_id="7.2-15",
            clause="7.2",
            test_number="15",
            description="description",
            context="context",
            message="message",
        ),
        None,
        cell_d,
    )[0]

    assert supplementary_information.affected_cell_id == affected_cell_id
    assert len(supplementary_information.correction_plans) == 1

    plan = supplementary_information.correction_plans[0]
    assert plan.cell_to_remove_id == affected_cell_id
    assert plan.span_adjustment is None
    assert plan.intersection.overlapped_cell_id == affected_cell_id
    assert plan.intersection.other_cell_id == _find_cell_id(id_mapping, "C")
    assert supplementary_information.logical_grid.slot_to_cell_id[(1, 2)] == _find_cell_id(
        id_mapping, "C"
    )


def test_collect_supplementary_information_7_2_t15_overlapped_cell_with_mcids_gets_span_adjustment():
    """
    Same layout as the removal case, but the affected cell contains an MCID.
    The collector plans a /RowSpan reduction on the blocking cell instead of removal.
    """
    cell_a = _make_cell(marker="A")
    cell_b = _make_cell(marker="B")
    cell_c = _make_cell(marker="C", row_span=2)
    cell_d = _make_cell(marker="D", col_span=3, content=[_make_content_child(mcid=7)])
    table = _make_table(_make_row(cell_a, cell_b, cell_c), _make_row(cell_d))
    _wire_table_parents(table)

    id_mapping = generate_id_to_table_elements_mapping(table)
    affected_cell_id = _find_cell_id(id_mapping, "D")
    blocking_cell_id = _find_cell_id(id_mapping, "C")

    supplementary_information = collect_supplementary_information_7_2_t15(
        VeraPdfViolation(
            rule_id="7.2-15",
            clause="7.2",
            test_number="15",
            description="description",
            context="context",
            message="message",
        ),
        None,
        cell_d,
    )[0]

    plan = supplementary_information.correction_plans[0]
    assert plan.cell_to_remove_id is None
    assert plan.span_adjustment is not None
    assert plan.span_adjustment.cell_id == blocking_cell_id
    assert plan.span_adjustment.new_row_span == 1
    assert plan.intersection.overlapped_cell_id == affected_cell_id


def test_table_grid_coordinate_as_slot_key():
    coordinate = TableGridCoordinate(row=2, column=3)
    assert coordinate.as_slot_key == (2, 3)


def test_find_ancestor_table_walks_parent_chain():
    cell = _make_cell(marker="cell")
    row = _make_row(cell)
    table = _make_table(row)
    cell["/P"] = row
    row["/P"] = table

    assert find_ancestor_table(cell) == table


def test_collect_table_rows_in_order_handles_tbody_wrapper():
    td = _make_cell()
    tr = _make_row(td)
    tbody = Dictionary({"/S": Name("/TBody"), "/K": Array([tr])})
    table = _make_table(tbody)

    rows = collect_table_rows_in_order(table)
    assert rows == [tr]


def test_analyze_table_grid_returns_no_plans_for_valid_table():
    table = _make_table(
        _make_row(_make_cell(marker="A"), _make_cell(marker="B")),
        _make_row(_make_cell(marker="C"), _make_cell(marker="D")),
    )
    id_mapping = generate_id_to_table_elements_mapping(table)

    analysis = analyze_table_grid(table, id_mapping, _find_cell_id(id_mapping, "C"))
    assert analysis.correction_plans == []


def test_collect_supplementary_information_7_2_t15_ignores_other_intersections():
    """
    Table with two overlapping cells; only the veraPDF-reported affected cell gets a plan.

        Row 0: [TD A] [TD B] [TD C (RowSpan=3)]
        Row 1: [TD E (ColSpan=3, empty)]  <- also overlaps, but not affected
        Row 2: [TD D (ColSpan=3, empty)]  <- affected cell
    """
    cell_a = _make_cell(marker="A")
    cell_b = _make_cell(marker="B")
    cell_c = _make_cell(marker="C", row_span=3)
    cell_e = _make_cell(marker="E", col_span=3)
    cell_d = _make_cell(marker="D", col_span=3)
    table = _make_table(
        _make_row(cell_a, cell_b, cell_c),
        _make_row(cell_e),
        _make_row(cell_d),
    )
    _wire_table_parents(table)

    supplementary_information = collect_supplementary_information_7_2_t15(
        VeraPdfViolation(
            rule_id="7.2-15",
            clause="7.2",
            test_number="15",
            description="description",
            context="context",
            message="message",
        ),
        None,
        cell_d,
    )[0]

    assert len(supplementary_information.correction_plans) == 1
    assert supplementary_information.correction_plans[0].intersection.overlapped_cell_id == _find_cell_id(
        supplementary_information.id_to_table_elements_mapping, "D"
    )


def test_collect_supplementary_information_7_2_t15_rejects_non_table_cell():
    with pytest.raises(ValueError, match="/TD or /TH"):
        collect_supplementary_information_7_2_t15(
            VeraPdfViolation(
                rule_id="7.2-15",
                clause="7.2",
                test_number="15",
                description="description",
                context="context",
                message="message",
            ),
            None,
            Dictionary({"/S": Name("/TR")}),
        )
