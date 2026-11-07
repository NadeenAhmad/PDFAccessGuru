from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


@corrector("charset-incorrectly-lists-glyphs")
def correct_charset_incorrectly_lists_glyphs(
    detected_violation: DetectedViolation,
    pdf: Pdf,
):
    """
    Corrects VeraPDF rule 7.21.4.2-1 by removing an incorrect /CharSet
    entry from the affected font's FontDescriptor.

    The violation provides the affected font object directly. The
    corrector accesses its FontDescriptor and removes /CharSet if it is
    present. If the font does not contain a FontDescriptor, the violation
    cannot be corrected because there is no location from which the
    incorrect /CharSet entry could be removed.
    """

    font_obj = detected_violation.affected_element
    font_descriptor = font_obj.get("/FontDescriptor")

    if font_descriptor is None:
        raise CouldNotCorrectDetectedViolationException(
            "kein FontDescriptor vorhanden"
        )

    if "/CharSet" in font_descriptor:
        del font_descriptor["/CharSet"]
