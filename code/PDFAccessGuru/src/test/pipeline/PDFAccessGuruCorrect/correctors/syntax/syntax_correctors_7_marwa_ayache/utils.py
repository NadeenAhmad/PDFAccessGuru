from pathlib import Path

from pikepdf import Object

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.supplementary_information.supplementary_information import SupplementaryInformation
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.utils.compare_segment_parsing import have_equal_segment_parsing


def generate_resource_path(path: str) -> str:
    """Return the absolute path below src/test/resources."""
    return str(Path(__file__).resolve().parents[5] / "resources" / path)


def generate_test_output_path(filename: str) -> Path:
    """Return a stable output path below the test packages test_results directory."""
    output_dir = Path(__file__).resolve().parents[5] / "test_results"
    output_dir.mkdir(exist_ok=True)
    return output_dir / filename


def build_detected_syntax_violation(
    name: str,
    affected_element: Object,
    supplementary_information: list[SupplementaryInformation] | None = None,
) -> DetectedViolation:
    """Create the minimal DetectedViolation object needed by a corrector test."""
    violation = Violation(
        category=ViolationCategory.SYNTAX,
        name=name,
        description="",
        guidelines=[],
    )
    return DetectedViolation(
        violation=violation,
        affected_element=affected_element,
        supplementary_information=supplementary_information or [],
    )


def assert_verapdf_violation_removed(
    pdf_path: str,
    rule_id: str,
    context_path: str,
) -> None:
    """
    Assert that veraPDF no longer reports the same rule at the same context.

    We compare the parsed context segments instead of the raw string because
    veraPDF may vary object decorations like "(12 0 obj ...)".
    """
    verapdf_violations = run_verapdf(pdf_path)
    for verapdf_violation in verapdf_violations:
        same_rule = verapdf_violation.rule_id == rule_id
        same_context = have_equal_segment_parsing(verapdf_violation.context, context_path)
        assert not (same_rule and same_context), (
            f"veraPDF still reports rule {rule_id} at context {context_path}: "
            f"{verapdf_violation}"
        )


def build_verapdf_violation(rule_id: str, context_path: str) -> VeraPdfViolation:
    clause, test_number = rule_id.rsplit("-", 1)
    return VeraPdfViolation(
        rule_id=rule_id,
        clause=clause,
        test_number=test_number,
        description="",
        context=context_path,
        message="",
    )
