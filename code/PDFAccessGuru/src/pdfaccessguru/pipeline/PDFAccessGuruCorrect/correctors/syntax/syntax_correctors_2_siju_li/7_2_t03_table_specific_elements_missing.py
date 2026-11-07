from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tables import CellsWithoutRows, TableRepair
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles


@corrector("table-specific-elements-missing")
def correct_table_specific_elements_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-3
    Violation: a Table contains something other than TR, THead, TBody, TFoot or Caption.

    Fix (whole table at once, see structure_repair/tables.py):
    - loose cells are put into rows by their position on the page;
    - grouping tags around rows are removed, empty tags are removed;
    - other content at the start or end becomes the caption if it reads like one
      ("Table 3: ..."), otherwise it is moved just outside the table, so the reading order
      stays the same; content in the middle becomes a row with one cell across all columns.
    The earlier version renamed such content (e.g. a paragraph) to a table row.
    """
    element = detected_violation.affected_element
    if not isinstance(element, Dictionary) or not Roles(pdf).is_(element, "Table"):
        raise CouldNotCorrectDetectedViolationException("table-specific-elements-missing: the affected element is not a Table")
    try:
        TableRepair(pdf).repair_group(element)
    except CellsWithoutRows as error:
        raise CouldNotCorrectDetectedViolationException("the positions of the loose table cells are unknown and the table has no rows to compare with, so their rows cannot be worked out") from error
