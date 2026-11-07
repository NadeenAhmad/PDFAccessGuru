import pytest

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_charset_incorrectly_lists_glyphs,
)


def test_correct_charset_incorrectly_lists_glyphs():
    """
    Testet die Korrektur für Regel 7.21.6‑3:
    Entfernt den /Encoding‑Schlüssel aus einem symbolischen TrueType‑Font‑Dictionary.
    """
    run_generic_corrector_test(
        rule_id="7.21.4.2-1",
        test_pdf_file="veraPDF_corpus/7.21.4.2-t01-fail-a.pdf",   
        corrector=correct_charset_incorrectly_lists_glyphs,
        context=(
            "root/document[0]/pages[0](17 0 obj PDPage)/contentStream[0](19 0 obj PDSemanticContentStream)/operators[6]/font[0](MIJADQ+AdobeNaskh-Medium)"
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj["/Resources"]["/Font"]["/T1_0"]
    )
    
