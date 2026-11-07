from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tables import CellsWithoutRows, TableRepair
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles


@corrector("th-td-missing")
def correct_th_td_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-10
    Violation: a row (TR) contains something other than header or data cells.

    Fix (see structure_repair/tables.py): empty tags are removed; content that sits inside a
    cell's area on the page joins that cell; otherwise it becomes a cell of its own if the row
    has fewer cells than the table has columns, and joins the cell before it if the row is
    already full. The earlier version wrapped every piece in its own cell, which changed the
    number of columns.
    """
    element = detected_violation.affected_element
    if not isinstance(element, Dictionary) or not Roles(pdf).is_(element, "TR"):
        raise CouldNotCorrectDetectedViolationException("th-td-missing: the affected element is not a TR")
    TableRepair(pdf).repair_row(element)
