from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi import (
    correct_suspects_entry_true,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)


def test_correct_suspects_entry_true():
    run_generic_corrector_test(
        rule_id="7.1-4",
        test_pdf_file="veraPDF_corpus/7.1-t04-fail-a.pdf",
        corrector=correct_suspects_entry_true,
        context="root",
        affected_element_detector=lambda pdf: pdf.Root.get("/MarkInfo"),  # type: ignore
    )
