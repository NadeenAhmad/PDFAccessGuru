import pytest

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_cmap_references_another_non_standard_cmap,
)


def test_correct_cmap_references_another_non_standard_cmap_veraPDF():

    run_generic_corrector_test(
        rule_id="7.21.3.3-1",
        test_pdf_file="veraPDF_corpus/7.21.3.3-t01-fail-a.pdf",   # Beispiel-Datei aus dem veraPDF-Corpus
        corrector=correct_cmap_references_another_non_standard_cmap,
        context=(
            "root/document[0]/pages[0](17 0 obj PDPage)/contentStream[0](25 0 obj PDSemanticContentStream)/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)/Encoding[0]"  # beliebiger Kontext
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj["/Resources"]["/Font"]["/C0_0"]
    )