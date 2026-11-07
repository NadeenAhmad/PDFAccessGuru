import pytest

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)
from .run_generic_supplementary_information import (
    run_generic_supplementary_information_corrector_test,
)

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_glyph_invalid_unicode,
)

def test_correct_glyph_invalid_unicode():
    """
    
    """

    def affected_element_detector(pdf):
        return pdf.pages[0].obj["/Resources"]["/Font"]["/TT0"]["/ToUnicode"]



    def supplementary_information_extractor(pdf):
        
        context = pdf.pages[0].obj["/Contents"]
        toUnicode = pdf.pages[0].obj["/Resources"]["/Font"]["/TT0"]["/ToUnicode"]
        raw_stream = toUnicode.read_bytes()
        toUnicode_text = raw_stream.decode("utf-8", errors="ignore")
        print ("toUnicode ", toUnicode_text)  
        wrongMappings = [
    {
        "type": "bfchar",
        "src": "<01>",
        "dst": "<feff>",
        "unicode": "U+FEFF"
    }
]

        

        # Rückgabe als flache Liste: [Font-Objekt, used_codes]
        return wrongMappings



    run_generic_supplementary_information_corrector_test(
        rule_id="7.21.7-2",
        test_pdf_file="veraPDF_corpus/7.21.7-t02-fail-c.pdf",
        corrector=correct_glyph_invalid_unicode,
        context=(
            "root/document[0]/pages[0](4 0 obj PDPage)/contentStream[0](13 0 obj PDSemanticContentStream)/operators[9]/usedGlyphs[0](BAAAAA+TimesNewRomanPSMT BAAAAA+TimesNewRomanPSMT 1 0 1233595751 0 true)"
        ),
        affected_element_detector=affected_element_detector,
        supplementary_information_extractor=supplementary_information_extractor,
    )    
  