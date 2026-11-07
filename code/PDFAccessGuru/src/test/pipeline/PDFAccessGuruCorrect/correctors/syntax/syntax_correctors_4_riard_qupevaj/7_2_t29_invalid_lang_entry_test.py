from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import (
    correct_invalid_lang_entry,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.test_utils import (
    run_generic_corrector_test,
)


def test_correct_invalid_lang_entry():
    run_generic_corrector_test(
        rule_id="7.2-29",
        test_pdf_file="veraPDF_corpus/7.2-t29-fail-a.pdf",
        corrector=correct_invalid_lang_entry,
        context="root/document[0]/Lang[0]",
        affected_element_detector=lambda pdf: pdf.Root.get("/Lang"),
    )
