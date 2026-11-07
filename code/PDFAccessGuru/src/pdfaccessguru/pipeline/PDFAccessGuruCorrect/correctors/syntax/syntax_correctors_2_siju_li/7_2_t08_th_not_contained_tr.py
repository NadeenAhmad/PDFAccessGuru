from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tables import CellsWithoutRows, TableRepair
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles


@corrector("th-not-contained-tr")
def correct_th_not_contained_tr(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-8
    Violation: a header cell (TH) is not inside a row (TR).

    Fix: all loose cells of the table part are put into rows at once. Cells on the same line
    of the page form one row; without positions, rows get as many cells as the table's other
    rows. The earlier version put all loose cells into a single row.
    """
    element = detected_violation.affected_element
    if not isinstance(element, Dictionary) or not Roles(pdf).is_(element, "TH"):
        raise CouldNotCorrectDetectedViolationException("th-not-contained-tr: the affected element is not a TH")
    try:
        TableRepair(pdf).repair_loose_cell(element)
    except CellsWithoutRows as error:
        raise CouldNotCorrectDetectedViolationException("the positions of the loose table cells are unknown and the table has no rows to compare with, so their rows cannot be worked out") from error
