import pikepdf
from pikepdf import Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.correct_id_note_tag_non_unique import correct_id_note_tag_non_unique
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


@corrector("id-note-tag-missing")
def correct_id_note_tag_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.9-1

    Violation description:
    ID key of the Note tag is not present.

    Correction strategy:
    Simply add the `/ID` attribute with the value `Note`.
    """
    affected_element = detected_violation.affected_element
    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("id-note-tag-missing")

    affected_element["/ID"] = "Note"

    correct_id_note_tag_non_unique(detected_violation, pdf)  # Ensure uniqueness after adding the ID
