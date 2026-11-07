import pytest

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)
from .run_generic_supplementary_information import (
    run_generic_supplementary_information_corrector_test,
)

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_referenced_glyphs_missing,

)

def test_correct_referenced_glyphs_missing_veraPDF():
    """
    Tests correction of missing embedded font programs (7.21.4.1-1).
    """

    def affected_element_detector(pdf):
        return None



    def supplementary_information_extractor(pdf):

        #Trailer > /Root > /Pages > /Kids > [0] > /Resources > /Font > /C2_0
        font = pdf.pages[0].obj["/Resources"]["/Font"]["/C2_0"]
        print("font", font)
        
        used_codes = {3, 68, 72, 42, 74, 79, 82, 83, 86, 87, 65535}
        

        # Rückgabe als flache Liste: [Font-Objekt, used_codes]
        return font, used_codes



    run_generic_supplementary_information_corrector_test(
        rule_id="7.21.4.1-2",
        test_pdf_file="PDFAccessGuru_corpus/7.21.4.1-t02-fail-a.pdf",
        corrector=correct_referenced_glyphs_missing,
        context=(
            "root/document[0]/pages[0](4 0 obj PDPage)/contentStream[0](13 0 obj PDSemanticContentStream)/operators[9]/usedGlyphs[0](BAAAAA+TimesNewRomanPSMT BAAAAA+TimesNewRomanPSMT 1 0 1233595751 0 true)"
        ),
        affected_element_detector=affected_element_detector,
        supplementary_information_extractor=supplementary_information_extractor,
    )    
  