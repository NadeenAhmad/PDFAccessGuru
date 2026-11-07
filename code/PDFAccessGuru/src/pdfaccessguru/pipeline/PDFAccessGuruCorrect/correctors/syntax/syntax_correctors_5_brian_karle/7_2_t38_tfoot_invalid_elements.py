from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tables import CellsWithoutRows, TableRepair
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles


@corrector("tfoot-invalid-elements")
def correct_tfoot_invalid_elements(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-38
    Violation: a TFoot contains something other than rows (TR).

    Fix (see structure_repair/tables.py): empty tags are removed; loose cells are put into
    rows by their position on the page (cells on the same line form one row); grouping tags
    around rows are removed; other content joins the cell whose area contains it, or becomes
    a row with one cell across all columns. The earlier version turned every cell into its
    own row.
    """
    element = detected_violation.affected_element
    if not isinstance(element, Dictionary) or not Roles(pdf).is_(element, "TFoot"):
        raise CouldNotCorrectDetectedViolationException("tfoot-invalid-elements: the affected element is not a TFoot")
    try:
        TableRepair(pdf).repair_group(element)
    except CellsWithoutRows as error:
        raise CouldNotCorrectDetectedViolationException("the positions of the loose table cells are unknown and the table has no rows to compare with, so their rows cannot be worked out") from error
