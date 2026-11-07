from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import (
    correct_toc_contains_invalid_element,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.test_utils import (
    run_generic_corrector_test,
)


def test_correct_toc_contains_invalid_element():
    run_generic_corrector_test(
        rule_id="7.2-27",
        test_pdf_file="veraPDF_corpus/7.2-t27-fail-c.pdf",
        corrector=correct_toc_contains_invalid_element,
        context="root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](18 0 obj SEDocument Document)/K[0](31 0 obj SETOC TOC)",
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[0],
    )
