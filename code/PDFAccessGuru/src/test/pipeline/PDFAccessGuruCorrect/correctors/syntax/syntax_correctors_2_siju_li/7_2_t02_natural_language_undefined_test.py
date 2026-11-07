import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li import (
    correct_natural_language_undefined,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    generate_test_result_path,
    generate_resource_path,
)


def test_correct_natural_language_undefined():
    """
    Test for rule 7.2-2: Natural language is not defined at document level.
    
    This test verifies that the corrector adds a /Lang entry to the document root.
    """
    violation = Violation(
        category=ViolationCategory.SYNTAX,
        name="natural-language-undefined",
        description="",
        guidelines=[]
    )
    
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t02-fail-a.pdf")
    result_path = generate_test_result_path("7.2-t02-fail-a_corrected.pdf")
    
    with pikepdf.open(pdf_path) as pdf:
        detected_violation = DetectedViolation(
            violation=violation,
            affected_element=pdf.Root,
            supplementary_information=[]
        )
        
        correct_natural_language_undefined(detected_violation, pdf)
        pdf.save(result_path)
    
    # Verify with veraPDF
    verapdf_violations = run_verapdf(result_path)
    
    for v_violation in verapdf_violations:
        assert v_violation.rule_id != "7.2-2"
