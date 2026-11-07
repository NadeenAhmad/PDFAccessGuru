import importlib

import pytest
from pikepdf import Array, Dictionary, Integer, Name
import pikepdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.supplementary_information.supplementary_information import (
    SupplementaryInformation,
    TableCellIntersectionSupplementaryInformation,
)
from pdfaccessguru.model.supplementary_information.table.grid import (
    LogicalTableGrid,
    SpanAdjustment,
    TableCellCorrectionPlan,
    TableCellIntersection,
    TableGridCoordinate,
)
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart import (
    correct_table_cell_intersection_other_cells,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collectors_3_robin_hart.v7_2_t15_table_cell_intersection_other_cells import (
    collect_supplementary_information_7_2_t15,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.taxonomy_data_mapping.map_verapdf_violation_to_taxonomy_data import (
    map_rule_id_to_syntax_violation_name,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    generate_resource_path,
    generate_test_result_path,
)
from test.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.test_utils import (
    have_equal_segment_parsing,
)

t15 = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart."
    "7_2_t15_table_cell_intersection_other_cells"
)


def _require_dictionary(value: pikepdf.Object, label: str) -> pikepdf.Dictionary:
    if not isinstance(value, pikepdf.Dictionary):
        pytest.fail(f"Expected {label} to be a structure dictionary")
    return value


def _get_corpus_affected_td(pdf: pikepdf.Pdf) -> pikepdf.Dictionary:
    struct_root_value = pdf.Root.get("/StructTreeRoot")
    if struct_root_value is None:
        pytest.fail("Expected StructTreeRoot in PDF")
    struct_root = _require_dictionary(struct_root_value, "StructTreeRoot")
    document = _require_dictionary(struct_root["/K"][0], "document")
    table_kids = document["/K"]
    if isinstance(table_kids, pikepdf.Array):
        table = next(
            _require_dictionary(element, "table child")
            for element in table_kids
            if isinstance(element, pikepdf.Dictionary) and element.get("/S") == Name("/Table")
        )
    else:
        table = _require_dictionary(table_kids, "table")

    row = _require_dictionary(table["/K"][2], "affected row")
    return _require_dictionary(row["/K"][1], "affected TD")


def _make_table_attr(*, row_span: int | None = None, col_span: int | None = None) -> Dictionary:
    attr = Dictionary({"/O": Name("/Table")})
    if row_span is not None:
        attr["/RowSpan"] = Integer(row_span)
    if col_span is not None:
        attr["/ColSpan"] = Integer(col_span)
    return attr


def _make_cell(
    *,
    row_span: int | None = None,
    col_span: int | None = None,
    marker: str | None = None,
) -> Dictionary:
    cell_dict: dict = {"/S": Name("/TD")}
    if marker is not None:
        cell_dict["/Alt"] = marker
    if row_span is not None or col_span is not None:
        cell_dict["/A"] = _make_table_attr(row_span=row_span, col_span=col_span)
    return Dictionary(cell_dict)


def _make_row(*cells: Dictionary) -> Dictionary:
    return Dictionary({"/S": Name("/TR"), "/K": Array(cells)})


def _make_supplementary_information(
    *,
    correction_plans: list[TableCellCorrectionPlan],
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
    id_to_parent_tr_mapping: dict[int, pikepdf.Object],
) -> TableCellIntersectionSupplementaryInformation:
    return TableCellIntersectionSupplementaryInformation(
        table_element=Dictionary({"/S": Name("/Table")}),
        affected_cell_id=0,
        id_to_table_elements_mapping=id_to_table_elements_mapping,
        id_to_parent_tr_mapping=id_to_parent_tr_mapping,
        logical_grid=LogicalTableGrid(),
        correction_plans=correction_plans,
    )


def test_correct_table_cell_intersection_other_cells():
    """
    Integration test: affected element is the intersecting /TD reported by veraPDF.
    """
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t15-fail-a.pdf")
    context = (
        "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)"
        "/K[0](14 0 obj SEDocument Document)/K[0](24 0 obj SETable Table)"
        "/K[2](47 0 obj SETR TR)/K[1](30 0 obj SETD TD)"
    )

    with pikepdf.open(pdf_path) as pdf:
        affected_td = _get_corpus_affected_td(pdf)

        vera_pdf_violation = VeraPdfViolation(
            rule_id="7.2-15",
            clause="7.2",
            test_number="15",
            description="description",
            context=context,
            message="message",
        )
        supplementary_information = collect_supplementary_information_7_2_t15(
            vera_pdf_violation,
            pdf,
            affected_td,
        )
        detected_violation = DetectedViolation(
            violation=Violation(
                category=ViolationCategory.SYNTAX,
                name=map_rule_id_to_syntax_violation_name("7.2-15"),
                description="",
                guidelines=[],
            ),
            affected_element=affected_td,
            supplementary_information=supplementary_information,
        )
        correct_table_cell_intersection_other_cells(detected_violation, pdf)
        pdf.save(generate_test_result_path("PDFAccessGuru_corpus/7.2-t15-fail-a_corrected.pdf"))

    for verapdf_violation in run_verapdf(
        generate_test_result_path("PDFAccessGuru_corpus/7.2-t15-fail-a_corrected.pdf")
    ):
        assert verapdf_violation.rule_id != "7.2-15" or not have_equal_segment_parsing(
            verapdf_violation.context,
            context,
        )


def test_remove_cell_from_tr_removes_cell_from_array_k_entry():
    keep = _make_cell(marker="keep")
    remove = _make_cell(marker="remove")
    row = _make_row(keep, remove)
    t15._remove_cell_from_tr(row, remove)
    remaining = list(row["/K"])
    assert len(remaining) == 1
    assert remaining[0] == keep


def test_remove_cell_from_tr_deletes_k_when_cell_is_only_child():
    only_cell = _make_cell()
    row = Dictionary({"/S": Name("/TR"), "/K": only_cell})
    t15._remove_cell_from_tr(row, only_cell)
    assert "/K" not in row


def test_apply_span_adjustment_updates_rowspan():
    cell = _make_cell(row_span=2)
    mapping: dict[int, pikepdf.Object] = {3: cell}
    t15._apply_span_adjustment(mapping, SpanAdjustment(cell_id=3, new_row_span=1))
    assert int(cell["/A"]["/RowSpan"]) == 1


def test_correct_table_cell_intersection_other_cells_raises_without_supplementary_information():
    detected_violation = DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name=map_rule_id_to_syntax_violation_name("7.2-15"),
            description="",
            guidelines=[],
        ),
        affected_element=Dictionary({"/S": Name("/TD")}),
        supplementary_information=[],
    )
    with pytest.raises(CouldNotCorrectDetectedViolationException):
        correct_table_cell_intersection_other_cells(detected_violation, pikepdf.new())


def test_correct_table_cell_intersection_other_cells_removes_empty_overlapped_cell():
    remove = _make_cell(marker="remove")
    row = _make_row(remove)
    mapping: dict[int, pikepdf.Object] = {1: remove}
    parent_mapping: dict[int, pikepdf.Object] = {1: row}
    plan = TableCellCorrectionPlan(
        intersection=TableCellIntersection(
            overlapped_cell_id=1,
            other_cell_id=2,
            conflicting_slots=[TableGridCoordinate(row=1, column=2)],
        ),
        cell_to_remove_id=1,
    )
    supplementary_information: list[SupplementaryInformation] = [
        _make_supplementary_information(
            correction_plans=[plan],
            id_to_table_elements_mapping=mapping,
            id_to_parent_tr_mapping=parent_mapping,
        )
    ]
    detected_violation = DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name=map_rule_id_to_syntax_violation_name("7.2-15"),
            description="",
            guidelines=[],
        ),
        affected_element=remove,
        supplementary_information=supplementary_information,
    )
    correct_table_cell_intersection_other_cells(detected_violation, pikepdf.new())
    assert "/K" not in row


def test_is_same_structure_element_uses_objgen_for_indirect_objects():
    pdf = pikepdf.new()
    first = pdf.make_indirect(_make_cell(marker="a"))
    second = pdf.make_indirect(_make_cell(marker="a"))
    assert t15._is_same_structure_element(first, first) is True
    assert t15._is_same_structure_element(first, second) is False
