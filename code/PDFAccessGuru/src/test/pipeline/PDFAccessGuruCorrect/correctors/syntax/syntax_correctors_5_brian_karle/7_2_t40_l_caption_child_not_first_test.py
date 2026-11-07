import pytest
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle import (
    correct_l_caption_child_not_first,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)

def test_correct_l_caption_child_not_first():
    run_generic_corrector_test(
        rule_id="7.2-40",
        test_pdf_file="veraPDF_corpus/7.2-t19-fail-a.pdf",
        corrector=correct_l_caption_child_not_first,
        context=(
            "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)"
            "/K[0](15 0 obj SEDocument Document)"
            "/K[0](26 0 obj SEL L)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot")\
            .get("/K").get("/K"),  # type: ignore
    )