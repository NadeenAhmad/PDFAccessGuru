from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.protection import allow_screen_readers
from pdfaccessguru.pipeline.reporting.writer import report_info


@corrector("encrypted-file-p-missing")
def correct_encrypted_file_p_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.16-1
    Violation: the PDF is protected and its permissions do not let screen readers read it.

    Fix (Phase 4, optional): with the owner password (pdfaccessguru fix --ask-owner-password),
    the file is saved with the same passwords, encryption and permissions, plus the one for
    screen readers (see pipeline/protection.py). Without the password nothing is changed and the
    report says how the author can do it.
    """
    if not allow_screen_readers(pdf):
        raise CouldNotCorrectDetectedViolationException(
            "This PDF is protected and does not let screen readers read it. Run the tool again with the "
            "owner password (pdfaccessguru fix --ask-owner-password FILE), or ask the author to allow "
            "'content copying for accessibility' in the security settings.")
    report_info("The protection now lets screen readers read the text. "
                "The passwords and all other protection settings stay the same.")
