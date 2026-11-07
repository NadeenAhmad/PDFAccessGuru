from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import (
    correct_toc_caption_child,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.test_utils import (
    run_generic_corrector_test,
)


def test_correct_toc_caption_child():
    run_generic_corrector_test(
        rule_id="7.2-28",
        test_pdf_file="PDFAccessGuru_corpus/7.2-t28-fail-a.pdf",
        corrector=correct_toc_caption_child,
        context="root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[1](19 0 obj SETOC TOC)",
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[1],
    )
