from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import (
    correct_toci_missing_from_toc,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.test_utils import (
    run_generic_corrector_test,
)


def test_correct_toci_missing_from_toc():
    run_generic_corrector_test(
        rule_id="7.2-26",
        test_pdf_file="veraPDF_corpus/7.2-t26-fail-a.pdf",
        corrector=correct_toci_missing_from_toc,
        context="root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](18 0 obj SEDocument Document)/K[0](31 0 obj SENonStruct NonStruct)/K[1](55 0 obj SETOCI TOCI)",
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[0].get("/K")[1],
    )
