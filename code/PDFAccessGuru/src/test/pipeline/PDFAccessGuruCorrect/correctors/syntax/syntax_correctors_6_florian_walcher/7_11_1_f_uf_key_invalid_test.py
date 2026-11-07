from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_f_uf_key_invalid,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    run_generic_corrector_test,
)


def test_correct_f_uf_key_invalid():
    """
    Notes for detection: 
    
    """
    run_generic_corrector_test(
        rule_id="7.11-1",
        test_pdf_file="veraPDF_corpus/7.11-t01-fail-a.pdf",
        corrector=correct_f_uf_key_invalid,
        context=(
            "Trailer/Root/Names/EmbeddedFiles/Names[1]/F"
        ),
        affected_element_detector=lambda pdf: pdf.Root.Names.EmbeddedFiles # type: ignore
    )