from pikepdf import Array, Dictionary, Integer, Name, Object, Pdf
import pikepdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.supplementary_information.supplementary_information import (
    TableCellIntersectionSupplementaryInformation,
)
from pdfaccessguru.model.supplementary_information.table.grid import SpanAdjustment
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector

_CORRECTOR_ID = "table-cell-intersection-other-cells"


def _get_table_cell_intersection_supplementary_information(
    detected_violation: DetectedViolation,
) -> TableCellIntersectionSupplementaryInformation:
    for supplementary_information in detected_violation.supplementary_information:
        if isinstance(supplementary_information, TableCellIntersectionSupplementaryInformation):
            return supplementary_information

    raise CouldNotCorrectDetectedViolationException(_CORRECTOR_ID)


@corrector("table-cell-intersection-other-cells")
def correct_table_cell_intersection_other_cells(detected_violation: DetectedViolation, pdf: Pdf) -> None:
    """
    VeraPdf rule_id: 7.2-15
    Violation description: TD or TH element intersects other cells of the table

    Correction strategy:
    The affected element is the intersecting /TD or /TH cell reported by veraPDF.
    Supplementary information from the collector describes which slots overlap and
    whether the overlapped cell has visual content (MCIDs).

    If the overlapped cell has no MCIDs, it is removed from its parent /TR.
    Otherwise the collector-chosen cell has its /RowSpan or /ColSpan adjusted.
    """
    supplementary_information = _get_table_cell_intersection_supplementary_information(
        detected_violation
    )

    if not supplementary_information.correction_plans:
        raise CouldNotCorrectDetectedViolationException(_CORRECTOR_ID)

    for plan in supplementary_information.correction_plans:
        if plan.cell_to_remove_id is not None:
            cell_to_remove = supplementary_information.id_to_table_elements_mapping[plan.cell_to_remove_id]
            parent_tr = supplementary_information.id_to_parent_tr_mapping[plan.cell_to_remove_id]
            if not isinstance(cell_to_remove, pikepdf.Dictionary) or not isinstance(
                parent_tr, pikepdf.Dictionary
            ):
                raise CouldNotCorrectDetectedViolationException(_CORRECTOR_ID)
            _remove_cell_from_tr(parent_tr, cell_to_remove)
        elif plan.span_adjustment is not None:
            _apply_span_adjustment(
                supplementary_information.id_to_table_elements_mapping,
                plan.span_adjustment,
            )
        else:
            raise CouldNotCorrectDetectedViolationException(_CORRECTOR_ID)


def _is_same_structure_element(left: pikepdf.Object, right: pikepdf.Object) -> bool:
    if left.objgen != (0, 0) and right.objgen != (0, 0):
        return left.objgen == right.objgen
    return left == right


def _remove_cell_from_tr(parent_row: pikepdf.Dictionary, cell: pikepdf.Dictionary) -> None:
    row_children = parent_row["/K"]
    if isinstance(row_children, Array):
        corrected_row_children = Array()
        for row_child in row_children:
            if not _is_same_structure_element(row_child, cell):
                corrected_row_children.append(row_child)
        if len(corrected_row_children) == 0:
            del parent_row["/K"]
        else:
            parent_row["/K"] = corrected_row_children
    elif _is_same_structure_element(row_children, cell):
        del parent_row["/K"]


def _get_table_attribute_dict(cell: pikepdf.Dictionary) -> Dictionary | None:
    if "/A" not in cell:
        return None

    attrs = cell["/A"]
    attr_dicts = attrs if isinstance(attrs, pikepdf.Array) else [attrs]
    for attr_dict in attr_dicts:
        if isinstance(attr_dict, Dictionary) and attr_dict.get("/O") == Name("/Table"):
            return attr_dict
    return None


def _apply_span_adjustment(
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
    span_adjustment: SpanAdjustment,
) -> None:
    cell = id_to_table_elements_mapping[span_adjustment.cell_id]
    if not isinstance(cell, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException(_CORRECTOR_ID)

    table_attr = _get_table_attribute_dict(cell)
    if table_attr is None:
        raise CouldNotCorrectDetectedViolationException(_CORRECTOR_ID)

    if span_adjustment.new_row_span is not None:
        table_attr["/RowSpan"] = Integer(span_adjustment.new_row_span)
    if span_adjustment.new_col_span is not None:
        table_attr["/ColSpan"] = Integer(span_adjustment.new_col_span)
