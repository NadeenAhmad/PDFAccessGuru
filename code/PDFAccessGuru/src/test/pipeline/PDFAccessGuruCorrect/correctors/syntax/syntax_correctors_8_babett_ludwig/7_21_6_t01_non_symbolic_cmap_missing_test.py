# /Root > /Pages > /Kids > [0] > /Resources > /Font > /TT0
import pytest

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_non_symbolic_cmap_missing,
)


def test_correct_non_symbolic_cmap_missing():
    """

    """ #/Pages > /Kids > [0] > /Resources > /Font > /TT0
    run_generic_corrector_test(
        rule_id="7.21.6-1",
        test_pdf_file="PDFAccessGuru_corpus/7.21.6-t01-fail-a.pdf",   # Beispiel-Datei aus dem veraPDF-Corpus
        corrector=correct_non_symbolic_cmap_missing,
        context=(
            "root/document[0]/pages[0](10 0 obj PDPage)/contentStream[0](16 0 obj PDSemanticContentStream)/operators[6]/font[0](BIMHOB+IDAutomationHC39M)/fontFile[0]"  # beliebiger Kontext
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj["/Resources"]["/Font"]["/TT0"]
    )