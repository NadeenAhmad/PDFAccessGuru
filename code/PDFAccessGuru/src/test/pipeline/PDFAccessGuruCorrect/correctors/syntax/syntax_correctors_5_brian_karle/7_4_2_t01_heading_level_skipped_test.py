import pytest
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle import (
    correct_heading_level_skipped,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)

def test_correct_heading_level_skipped():
    run_generic_corrector_test(
        rule_id="7.4.2-1",
        test_pdf_file="veraPDF_corpus/7.4.2-t01-fail-a.pdf",
        corrector=correct_heading_level_skipped,
        context=(
            "root/document[0]/StructTreeRoot[0](20 0 obj PDStructTreeRoot)"
            "/K[0](27 0 obj SEDocument Document)"
            "/K[1](23 0 obj SEHn H2)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot")\
            .get("/K")[0].get("/K")[1],  # type: ignore
    )