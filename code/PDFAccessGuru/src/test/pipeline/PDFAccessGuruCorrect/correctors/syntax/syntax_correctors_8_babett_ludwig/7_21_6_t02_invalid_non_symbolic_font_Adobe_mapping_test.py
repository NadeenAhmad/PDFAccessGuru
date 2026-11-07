import pytest

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_invalid_non_symbolic_font_Adobe_mapping,
)


def test_correct_invalid_non_symbolic_font_Adobe_mapping_veraPDF1():
    """
    Testet die Korrektur für Regel 7.21.6‑3:
    Entfernt den /Encoding‑Schlüssel aus einem symbolischen TrueType‑Font‑Dictionary.
    """ #/Pages > /Kids > [0] > /Resources > /Font > /TT0
    run_generic_corrector_test(
        rule_id="7.21.6-3",
        test_pdf_file="veraPDF_corpus/7.21.6-t02-fail-a.pdf",   # Beispiel-Datei aus dem veraPDF-Corpus
        corrector=correct_invalid_non_symbolic_font_Adobe_mapping,
        context=(
            "root/document[0]/pages[0](22 0 obj PDPage)/contentStream[0](23 0 obj PDSemanticContentStream)/operators[5]/font[0](BIMHOB+IDAutomationHC39M)"  # beliebiger Kontext
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj["/Resources"]["/Font"]["/TT0"]
    )
    
    
def test_correct_invalid_non_symbolic_font_Adobe_mapping_veraPDF2():
    """
    Testet die Korrektur für Regel 7.21.6‑3:
    Entfernt den /Encoding‑Schlüssel aus einem symbolischen TrueType‑Font‑Dictionary.
    """ #/Pages > /Kids > [0] > /Resources > /Font > /TT0
    run_generic_corrector_test(
        rule_id="7.21.6-3",
        test_pdf_file="veraPDF_corpus/7.21.6-t02-fail-b.pdf",   # Beispiel-Datei aus dem veraPDF-Corpus
        corrector=correct_invalid_non_symbolic_font_Adobe_mapping,
        context=(
            "root/document[0]/pages[0](22 0 obj PDPage)/contentStream[0](23 0 obj PDSemanticContentStream)/operators[5]/font[0](BIMHOB+IDAutomationHC39M)"  # beliebiger Kontext
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj["/Resources"]["/Font"]["/TT0"]
    )
    
def test_correct_invalid_non_symbolic_font_Adobe_mapping_veraPDF3():
    """
    Testet die Korrektur für Regel 7.21.6‑3:
    Entfernt den /Encoding‑Schlüssel aus einem symbolischen TrueType‑Font‑Dictionary.
    """ #/Pages > /Kids > [0] > /Resources > /Font > /TT0
    run_generic_corrector_test(
        rule_id="7.21.6-3",
        test_pdf_file="veraPDF_corpus/7.21.6-t02-fail-c.pdf",   # Beispiel-Datei aus dem veraPDF-Corpus
        corrector=correct_invalid_non_symbolic_font_Adobe_mapping,
        context=(
            "root/document[0]/pages[0](26 0 obj PDPage)/contentStream[0](27 0 obj PDSemanticContentStream)/operators[5]/font[0](BIMHOB+IDAutomationHC39M)"  # beliebiger Kontext
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj["/Resources"]["/Font"]["/TT0"]
    )
    
def test_correct_invalid_non_symbolic_font_Adobe_mapping_veraPDF4():
    """
    Testet die Korrektur für Regel 7.21.6‑3:
    Entfernt den /Encoding‑Schlüssel aus einem symbolischen TrueType‑Font‑Dictionary.
    """ #/Pages > /Kids > [0] > /Resources > /Font > /TT0
    run_generic_corrector_test(
        rule_id="7.21.6-3",
        test_pdf_file="veraPDF_corpus/7.21.6-t02-fail-d.pdf",   # Beispiel-Datei aus dem veraPDF-Corpus
        corrector=correct_invalid_non_symbolic_font_Adobe_mapping,
        context=(
            "root/document[0]/pages[0](26 0 obj PDPage)/contentStream[0](41 0 obj PDSemanticContentStream)/operators[5]/font[0](BIMHOB+IDAutomationHC39M)"  # beliebiger Kontext
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj["/Resources"]["/Font"]["/TT0"]
    )