from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart import (
    correct_th_td_missing,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)


def test_correct_th_td_missing():
    """
    Notes for detection: 
    resolve_context is sufficient
    """
    run_generic_corrector_test(
        rule_id="7.2-10",
        test_pdf_file="veraPDF_corpus/7.2-t10-fail-a.pdf",
        corrector=correct_th_td_missing,
        context=(
            "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0]"
            "(15 0 obj SEDocument Document)/K[0](26 0 obj SETable Table)/K[0]"
            "(42 0 obj SETHead THead)/K[0](49 0 obj SETR TR)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot")\
            .get("/K").get("/K").get("/K")[0].get("/K"),  # type: ignore
    )
