import pikepdf
from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


@corrector("present-optional-content-configuration")
def correct_present_optional_content_configuration(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.10-2

    Violation description:
    Disallowed AS entry found in the optional content configuration.

    Correction strategy:
    Delete AS entry.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("present-optional-content-configuration")

    if "/AS" in affected_element:
        del affected_element["/AS"]
