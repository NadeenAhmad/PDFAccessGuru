from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.toc_and_headings import repair_toc_parent
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles


@corrector("toci-missing-from-toc")
def correct_toci_missing_from_toc(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-26
    Violation: a table-of-contents entry (TOCI) is not inside a table of contents (TOC).

    Fix (see structure_repair/toc_and_headings.py): consecutive loose entries form ONE table of
    contents, or join the table of contents right before or after them. The earlier version
    created a separate table of contents for every entry.
    """
    element = detected_violation.affected_element
    if not isinstance(element, Dictionary):
        raise CouldNotCorrectDetectedViolationException("toci-missing-from-toc: the affected element is not a structure element")
    parent = element.get("/P") if Roles(pdf).is_(element, "TOCI") else element
    if not isinstance(parent, Dictionary):
        raise CouldNotCorrectDetectedViolationException("toci-missing-from-toc: the entry has no parent")
    repair_toc_parent(pdf, parent)
