

import pytest

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_glyph_width_inconsistent,
)


def test_correct_glyph_width_inconsistent_veraPDF():

    run_generic_corrector_test(
        rule_id="7.21.5-1",
        test_pdf_file="veraPDF_corpus/7.21.5-t01-fail-a.pdf",   # Beispiel-Datei aus dem veraPDF-Corpus
        corrector=correct_glyph_width_inconsistent,
        context=(
            "root/document[0]/pages[0](14 0 obj PDPage)/contentStream[0](20 0 obj PDSemanticContentStream)/operators[6]/usedGlyphs[5](OPCPIB+TimesNewRomanPSMT OPCPIB+TimesNewRomanPSMT 32 0 1764773481 0 true)"  # beliebiger Kontext
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj["/Resources"]["/Font"]["/TT0"]
    )







