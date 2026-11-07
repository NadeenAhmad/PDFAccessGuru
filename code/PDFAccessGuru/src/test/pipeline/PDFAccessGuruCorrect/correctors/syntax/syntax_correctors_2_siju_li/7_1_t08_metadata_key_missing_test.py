import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li import (
    correct_metadata_key_missing,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    generate_test_result_path,
    generate_resource_path,
)


def test_correct_metadata_key_missing():
    """
    Test for rule 7.1-8: /Metadata entry is missing or invalid.
    
    This test verifies that the corrector properly adds or validates the metadata stream.
    """
    violation = Violation(
        category=ViolationCategory.SYNTAX,
        name="metadata-key-missing",
        description="",
        guidelines=[]
    )
    
    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t08-fail-a.pdf")
    result_path = generate_test_result_path("7.1-t08-fail-a_corrected.pdf")
    
    with pikepdf.open(pdf_path) as pdf:
        # For metadata, the affected_element is typically the document root
        detected_violation = DetectedViolation(
            violation=violation,
            affected_element=pdf.Root,
            supplementary_information=[]
        )
        
        correct_metadata_key_missing(detected_violation, pdf)
        pdf.save(result_path)
    
    # Verify with veraPDF
    verapdf_violations = run_verapdf(result_path)
    
    for v_violation in verapdf_violations:
        assert v_violation.rule_id != "7.1-8"
