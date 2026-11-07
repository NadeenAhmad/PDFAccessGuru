from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import (
    correct_natural_language_tu_form_fields_undefined,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.test_utils import (
    run_generic_corrector_test,
)


def test_correct_natural_language_tu_form_fields_undefined():
    run_generic_corrector_test(
        rule_id="7.2-25",
        test_pdf_file="veraPDF_corpus/7.2-t25-fail-a.pdf",
        corrector=correct_natural_language_tu_form_fields_undefined,
        context="root/document[0]/AcroForm[0]/formFields[0](3 0 obj PDTextField)",
        affected_element_detector=lambda pdf: pdf.Root.get("/AcroForm").get("/Fields")[0],
    )
