from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart import (
    correct_invalid_elements_li,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)


def test_correct_invalid_elements_li():
    """
    Notes for detection: 
    resolve_context is sufficient
    """
    run_generic_corrector_test(
        rule_id="7.2-20",
        test_pdf_file="veraPDF_corpus/7.2-t20-fail-a.pdf",
        corrector=correct_invalid_elements_li,
        context=(
            "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0]"
            "(15 0 obj SEDocument Document)/K[0](26 0 obj SEL L)/K[1](42 0 obj SELI LI)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot")\
            .get("/K").get("/K").get("/K")[1],  # type: ignore
    )
