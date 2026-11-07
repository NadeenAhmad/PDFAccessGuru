import pytest

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)
from .run_generic_supplementary_information import (
    run_generic_supplementary_information_corrector_test,
)

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_glyph_cannot_mapped_unicode,
)


# 7_21_7t01_glyph_cannot_mapped_unicode
def test_correct_glyph_cannot_mapped_unicode_veraPDF():
    """
    Tests correction of unmappable glyphs in ToUnicode streams
    (VeraPDF rule 7.21.7-1).

    page=0
    operator=6
    glyph=0
    font=/C2_0
    """

    def affected_element_detector(pdf):
        return pdf.pages[0]



    def supplementary_information_extractor(pdf):
        page = pdf.pages[0]
        operator_index = 6
        glyph_index = 0
        font_obj = pdf.pages[0].obj["/Resources"]["/Font"]["/C2_0"]

        return [page, operator_index, glyph_index, font_obj]



    run_generic_supplementary_information_corrector_test(
        rule_id="7.21.7-1",
        test_pdf_file="veraPDF_corpus/7.21.7-t01-fail-a.pdf",
        corrector=correct_glyph_cannot_mapped_unicode,
        context=(
            "root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](18 0 obj PDSemanticContentStream)/operators[6]/usedGlyphs[0](JAPTCA+AboriginalSerif JAPTCA+AboriginalSerif 40 0 1141113940 0 true)"
        ),
        affected_element_detector=affected_element_detector,
        supplementary_information_extractor=supplementary_information_extractor,
    )
     
     
       
    
    
def test_correct_glyph_cannot_mapped_unicode_validationSet():
    """

    """

    def affected_element_detector(pdf):
        return pdf.pages[0]



    def supplementary_information_extractor(pdf):
        page = pdf.pages[0]
        operator_index = 486
        glyph_index = 0
        font_obj = pdf.pages[0].obj["/Resources"]["/Font"]["/R53"]
        

        

        # Rückgabe als flache Liste: [Font-Objekt, used_codes]
        return [page, operator_index, glyph_index, font_obj]



    run_generic_supplementary_information_corrector_test(
        rule_id="7.21.7-1",
        test_pdf_file="validation_Set/functional_hyperlinks_FAILED_W2991007371_0.pdf",
        corrector=correct_glyph_cannot_mapped_unicode,
        context=(
            "root/document[0]/pages[0](5 0 obj PDPage)/contentStream[0](25 0 obj PDSemanticContentStream)/operators[486]/usedGlyphs[0](ASHJHL+CMEX10 ASHJHL+CMEX10 80 0 0 true)"
        ),
        affected_element_detector=affected_element_detector,
        supplementary_information_extractor=supplementary_information_extractor,
    )    
  