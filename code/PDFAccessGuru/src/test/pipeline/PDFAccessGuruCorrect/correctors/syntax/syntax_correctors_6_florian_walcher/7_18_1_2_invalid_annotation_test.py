from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_invalid_annotation,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    run_generic_corrector_test,
)


def test_correct_invalid_annotation():
    """
    Notes for detection: 
    
    """
    run_generic_corrector_test(
        rule_id="7.18.1-2",
        test_pdf_file="veraPDF_corpus/7.18.1-t02-fail-a.pdf",
        corrector=correct_invalid_annotation, # type: ignore
        context=(
            "root/document[0]/pages[0](10 0 obj PDPage)/annots[0](16 0 obj PDMarkupAnnot)"
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj.get("/Annots")[0] # type: ignore
    )