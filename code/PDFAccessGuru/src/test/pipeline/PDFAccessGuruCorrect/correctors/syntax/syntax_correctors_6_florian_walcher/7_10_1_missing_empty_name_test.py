from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_missing_empty_name,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    run_generic_corrector_test,
)


def test_correct_missing_empty_name():
    """
    Notes for detection: 
    
    """
    run_generic_corrector_test(
        rule_id="7.10-1",
        test_pdf_file="veraPDF_corpus/7.10-t01-fail-a.pdf",
        corrector=correct_missing_empty_name,
        context=(
            "root/document[0]/OCProperties[0](3 0 obj PDOCProperties)/D[0]"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/OCProperties").get("/D") # type: ignore
    )