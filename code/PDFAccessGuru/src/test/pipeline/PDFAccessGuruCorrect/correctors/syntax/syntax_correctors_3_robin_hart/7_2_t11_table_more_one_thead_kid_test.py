from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart import (
    correct_table_more_one_thead_kid,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)


def test_correct_table_more_one_thead_kid():
    """
    Notes for detection: 
    resolve_context is sufficient
    """
    run_generic_corrector_test(
        rule_id="7.2-11",
        test_pdf_file="veraPDF_corpus/7.2-t11-fail-a.pdf",
        corrector=correct_table_more_one_thead_kid,
        context=(
            "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0]"
            "(19 0 obj SEDocument Document)/K[0](30 0 obj SETable Table)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot")\
            .get("/K").get("/K"),  # type: ignore
    )
