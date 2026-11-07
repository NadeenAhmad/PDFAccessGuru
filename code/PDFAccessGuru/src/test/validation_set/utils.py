from pathlib import Path

import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correct import correct
from pdfaccessguru.pipeline.PDFAccessGuruDetect.detect import detect
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf


TEST_ROOT = Path(__file__).resolve().parents[1]
VALIDATION_SET_DIR = TEST_ROOT / "resources" / "validation_Set"
VALIDATION_TEST_RESULTS_DIR = (
    TEST_ROOT / "test_results" / "validation_test_results"
)


def validation_pdf_path(filename: str) -> Path:
    """
    Return the absolute path to a PDF in src/test/resources/validation_Set.
    """
    return VALIDATION_SET_DIR / filename


def validation_output_path(filename: str) -> Path:
    """
    Return a stable path for corrected validation-set test outputs.
    """
    VALIDATION_TEST_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return VALIDATION_TEST_RESULTS_DIR / filename


def filter_detected_violations_by_name(
    detected_violations: list[DetectedViolation],
    violation_name: str,
) -> list[DetectedViolation]:
    """
    Keep only detected violations with the given taxonomy violation name.
    """
    return [
        detected_violation
        for detected_violation in detected_violations
        if detected_violation.violation.name == violation_name
    ]


def detect_validation_violations(
    pdf_path: Path,
    pdf: pikepdf.Pdf,
    violation_name: str,
) -> list[DetectedViolation]:
    """
    Run the normal detector and return detections for one violation name.
    """
    detected_violations = detect(str(pdf_path), pdf)
    return filter_detected_violations_by_name(detected_violations, violation_name)

def verapdf_rule_count(pdf_path: Path, rule_id: str) -> int:
    """
    Return how often veraPDF reports the given rule ID for a PDF.
    """
    return sum(1 for violation in run_verapdf(str(pdf_path)) if violation.rule_id == rule_id)



def correct_validation_violations(
    pdf: pikepdf.Pdf,
    detected_violations: list[DetectedViolation],
    output_filename: str,
    violation_name: str,
) -> Path:
    """
    Correct already-detected violations and save the output PDF.
    """
    assert detected_violations, f"No detected violations found for {violation_name}"

    result_path = validation_output_path(output_filename)
    #print("das wird korrigiert: ", detected_violations)
    correct(detected_violations, pdf)
    pdf.save(result_path)

    return result_path

