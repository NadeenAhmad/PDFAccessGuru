from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle import (
    correct_thead_invalid_elements,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)

def test_correct_thead_invalid_elements():
    run_generic_corrector_test(
        rule_id="7.2-36",
        test_pdf_file="veraPDF_corpus/7.2-t36-fail-a.pdf",
        corrector=correct_thead_invalid_elements,
        context=(
            "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)"
            "/K[0](15 0 obj SEDocument Document)"
            "/K[0](26 0 obj SETable Table)"
            "/K[0](42 0 obj SETHead THead)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot")\
            .get("/K").get("/K").get("/K")[0],  # type: ignore
    )