import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li import (
    correct_missing_metadata_stream_dc_title,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    generate_test_result_path,
    generate_resource_path,
)


def test_correct_missing_metadata_stream_dc_title():
    """
    Test for rule 7.1-9: the XMP metadata stream's dc:title is missing or empty.

    This verifies that the corrector writes a valid document title to the metadata stream.
    """
    violation = Violation(
        category=ViolationCategory.SYNTAX,
        name="missing-metadata-stream-dc-title",
        description="",
        guidelines=[],
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t09-fail-a.pdf")
    result_path = generate_test_result_path("7.1-t09-fail-a_corrected.pdf")

    with pikepdf.open(pdf_path) as pdf:
        detected_violation = DetectedViolation(
            violation=violation,
            affected_element=pdf.Root.get("/Metadata"),
            supplementary_information=[],
        )

        correct_missing_metadata_stream_dc_title(detected_violation, pdf)
        pdf.save(result_path)

    verapdf_violations = run_verapdf(result_path)
    for v_violation in verapdf_violations:
        assert v_violation.rule_id != "7.1-9"
