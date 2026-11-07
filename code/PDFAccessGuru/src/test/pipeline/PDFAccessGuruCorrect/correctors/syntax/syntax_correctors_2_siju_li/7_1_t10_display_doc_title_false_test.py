import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li import (
    correct_display_doc_title_false,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    generate_test_result_path,
    generate_resource_path,
)


def test_correct_display_doc_title_false():
    """
    Test for rule 7.1-10: ViewerPreferences/DisplayDocTitle is not set or false.
    
    This test verifies that the corrector sets DisplayDocTitle to true.
    """
    violation = Violation(
        category=ViolationCategory.SYNTAX,
        name="display-doc-title-false",
        description="",
        guidelines=[]
    )
    
    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t10-fail-a.pdf")
    result_path = generate_test_result_path("7.1-t10-fail-a_corrected.pdf")
    
    with pikepdf.open(pdf_path) as pdf:
        detected_violation = DetectedViolation(
            violation=violation,
            affected_element=pdf.Root,
            supplementary_information=[]
        )
        
        correct_display_doc_title_false(detected_violation, pdf)
        pdf.save(result_path)
    
    # Verify with veraPDF
    verapdf_violations = run_verapdf(result_path)
    
    for v_violation in verapdf_violations:
        assert v_violation.rule_id != "7.1-10"
