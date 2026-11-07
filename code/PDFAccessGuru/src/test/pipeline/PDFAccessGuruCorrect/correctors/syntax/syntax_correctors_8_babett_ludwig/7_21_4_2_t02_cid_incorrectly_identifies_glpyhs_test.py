import pytest

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_cid_incorrectly_identifies_glpyhs,
)



def test_correct_cid_incorrectly_identifies_glpyhs():
    """
    Testet die Korrektur für falsch gemappte Glyphs.
    """

    run_generic_corrector_test(
        rule_id="7.21.4.2-2",
        test_pdf_file="veraPDF_corpus/7.21.4.2-t02-fail-a.pdf",
        corrector=correct_cid_incorrectly_identifies_glpyhs,
        context=(
            "root/document[0]/pages[0](17 0 obj PDPage)"
            "/contentStream[0](18 0 obj PDSemanticContentStream)/operators[4]"
            "/font[0](XIGADL+FreeMonoBold)/DescendantFonts[0](XIGADL+FreeMonoBold)"
        ),
        affected_element_detector=lambda pdf: (
            pdf.trailer["/Root"]                      # Trailer -> Root
               ["/Pages"]                             # Root -> Pages
               ["/Kids"][0]                           # erste Page
               ["/Resources"]                         # Resources
               ["/Font"]["/C2_0"]                     # konkreter Font
               ["/DescendantFonts"][0]                # CIDFont
               ["/FontDescriptor"]                   # Zielobjekt
        ),
    )