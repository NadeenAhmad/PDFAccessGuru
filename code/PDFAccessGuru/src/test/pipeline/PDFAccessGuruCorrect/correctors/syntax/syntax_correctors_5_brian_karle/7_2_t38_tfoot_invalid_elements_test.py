from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle import (
    correct_tfoot_invalid_elements,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)

def test_correct_tfoot_invalid_elements():
    run_generic_corrector_test(
        rule_id="7.2-38",
        test_pdf_file="veraPDF_corpus/7.2-t38-fail-a.pdf",
        corrector=correct_tfoot_invalid_elements,
        context=(
            "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)"
            "/K[0](15 0 obj SEDocument Document)"
            "/K[0](26 0 obj SETable Table)"
            "/K[3](45 0 obj SETFoot TFoot)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot")\
            .get("/K").get("/K").get("/K")[3],  # type: ignore
    )