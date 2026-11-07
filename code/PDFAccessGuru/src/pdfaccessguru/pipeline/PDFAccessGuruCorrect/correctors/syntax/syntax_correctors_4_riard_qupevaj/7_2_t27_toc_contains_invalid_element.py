from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.toc_and_headings import repair_toc
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles


@corrector("toc-contains-invalid-element")
def correct_toc_contains_invalid_element(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-27
    Violation: a table of contents (TOC) contains something other than entries (TOCI), nested
    tables of contents or a caption.

    Fix (see structure_repair/toc_and_headings.py): a reference or paragraph starts a new entry;
    other loose content (often the page number) joins the entry before it. Marked content that
    moves is re-registered, so screen readers still find its owner.
    """
    element = detected_violation.affected_element
    if not isinstance(element, Dictionary) or not Roles(pdf).is_(element, "TOC"):
        raise CouldNotCorrectDetectedViolationException("toc-contains-invalid-element: the affected element is not a TOC")
    repair_toc(pdf, element)
