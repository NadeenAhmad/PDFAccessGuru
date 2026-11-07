import pikepdf
import pytest

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_encrypted_file_p_missing,
)
from pdfaccessguru.pipeline.protection import start_run
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    generate_resource_path,
)


def test_without_the_owner_password_the_permissions_are_left_unchanged():
    """Changing the permissions needs the owner password (Phase 4b); without it nothing changes.
    The fix with a password is tested in src/test/pipeline/annotations_and_protection_test.py."""
    start_run(None)
    with pikepdf.open(generate_resource_path("veraPDF_corpus/7.16-t01-fail-a.pdf")) as pdf:
        before = int(pdf.trailer.Encrypt.P)
        violation = DetectedViolation(
            violation=Violation(category=ViolationCategory.SYNTAX, name="encrypted-file-p-missing",
                                description="", guidelines=[]),
            affected_element=pdf.trailer.get("/Encrypt"), supplementary_information=[])
        with pytest.raises(CouldNotCorrectDetectedViolationException, match="owner password"):
            correct_encrypted_file_p_missing(violation, pdf)
        assert int(pdf.trailer.Encrypt.P) == before
