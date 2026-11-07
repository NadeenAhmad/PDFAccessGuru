from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_formula_structure_no_alternative_description,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    run_generic_corrector_test,
)


def test_correct_formula_structure_no_alternative_description():
    """
    Notes for detection: 
    
    """
    run_generic_corrector_test(
        rule_id="7.7-1",
        test_pdf_file="veraPDF_corpus/7.7-t01-fail-a.pdf",
        corrector=correct_formula_structure_no_alternative_description,
        context=(
            "root/document[0]/StructTreeRoot[0](2 0 obj PDStructTreeRoot)/K[0](9 0 obj SEDocument Document)/K[1](18 0 obj SEFormula Formula)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1] # type: ignore
    )