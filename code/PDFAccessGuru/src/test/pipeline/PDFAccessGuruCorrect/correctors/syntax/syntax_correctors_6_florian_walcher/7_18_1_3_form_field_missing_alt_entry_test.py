from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_form_field_missing_alt_entry,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    run_generic_corrector_test,
)


def test_correct_form_field_missing_alt_entry():
    """
    Notes for detection: 
    
    """
    run_generic_corrector_test(
        rule_id="7.18.1-3",
        test_pdf_file="veraPDF_corpus/7.18.1-t01-fail-a.pdf",
        corrector=correct_form_field_missing_alt_entry,
        context=(
            "root/document[0]/pages[0](52 0 obj PDPage)/annots[0](39 0 obj PDWidgetAnnot)"
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj.get("/Annots")[0] # type: ignore
    )