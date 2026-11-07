from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_dynamic_xfa_forms_present,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    run_generic_corrector_test,
)


def test_correct_dynamic_xfa_forms_present():
    """
    Notes for detection: 
    
    """
    run_generic_corrector_test(
        rule_id="7.15-1",
        test_pdf_file="veraPDF_corpus/7.15-t01-fail-a.pdf",
        corrector=correct_dynamic_xfa_forms_present,
        context=(
            "root/document[0]/AcroForm[0](2 0 obj PDAcroForm)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/AcroForm") # type: ignore
    )