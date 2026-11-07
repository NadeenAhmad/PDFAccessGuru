from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_info, report_review


@corrector("suspects-entry-true")
def correct_suspects_entry_true(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.1-4
    Violation: /MarkInfo /Suspects is true: the program that made the tags was not sure they
    are right (typical after automatic tagging).

    Fix: /Suspects is set to false so that the file can pass, and the report says plainly that
    the tags themselves were not checked for meaning. The first version did this silently.
    """
    mark_info = pdf.Root.get("/MarkInfo")
    if not isinstance(mark_info, Dictionary) or "/Suspects" not in mark_info:
        raise CouldNotCorrectDetectedViolationException("suspects-entry-true: the file has no Suspects entry")
    mark_info["/Suspects"] = False
    message = ("The program that made this PDF marked its tags as possibly wrong. The mark was removed, "
               "but the tags were not checked for meaning. Please check headings, lists and reading order.")
    report_info(message)
    report_review(message)
