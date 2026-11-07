import pytest

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_wmode_embedded_cmap_not_identical,
)


def test_correct_wmode_embedded_cmap_not_identical_veraPDF1():

    run_generic_corrector_test(
        rule_id="7.21.3.3-2",
        test_pdf_file="veraPDF_corpus/7.21.3.3-t02-fail-a.pdf",   # Beispiel-Datei aus dem veraPDF-Corpus
        corrector=correct_wmode_embedded_cmap_not_identical,
        context=(
            "root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](22 0 obj PDSemanticContentStream)/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)/Encoding[0](30 0 obj PDCMap)/embeddedFile[0]"  # beliebiger Kontext
        ),#Trailer > /Root > /Pages > /Kids > [0] > /Resources > /Font > /C0_0
        affected_element_detector=lambda pdf: pdf.pages[0].obj["/Resources"]["/Font"]["/C0_0"]["/Encoding"]
    )
    
def test_correct_wmode_embedded_cmap_not_identical_veraPDF2():

    run_generic_corrector_test(
        rule_id="7.21.3.3-2",
        test_pdf_file="veraPDF_corpus/7.21.3.3-t02-fail-b.pdf",   # Beispiel-Datei aus dem veraPDF-Corpus
        corrector=correct_wmode_embedded_cmap_not_identical,
        context=(
            "root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](22 0 obj PDSemanticContentStream)/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)/Encoding[0](30 0 obj PDCMap)/embeddedFile[0]"  # beliebiger Kontext
        ),#Trailer > /Root > /Pages > /Kids > [0] > /Resources > /Font > /C0_0
        affected_element_detector=lambda pdf: pdf.pages[0].obj["/Resources"]["/Font"]["/C0_0"]["/Encoding"]
    )