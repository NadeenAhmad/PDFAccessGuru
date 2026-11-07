import pytest

from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)
from .run_generic_supplementary_information import (
    run_generic_supplementary_information_corrector_test,
)

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_embedded_font_program_multiple_cmap_subtables,
)

def test_correct_embedded_font_program_multiple_cmap_subtables():
    """

    """
    run_generic_corrector_test(
        rule_id="7.21.6-4",
        test_pdf_file="PDFAccessGuru_corpus/7.21.6-t04-fail-a.pdf",   
        corrector=correct_embedded_font_program_multiple_cmap_subtables,
        context=(
            "root/document[0]/pages[0](4 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/operators[10]/font[0](BAAAAA+Verdana)/fontFile[0]"
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj["/Resources"]["/Font"]["/TT0"]
    )
