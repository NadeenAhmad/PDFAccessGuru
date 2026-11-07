from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import (
    correct_natural_language_annotations_undefined,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.test_utils import (
    run_generic_corrector_test,
)


def test_correct_natural_language_annotations_undefined():
    run_generic_corrector_test(
        rule_id="7.2-24",
        test_pdf_file="veraPDF_corpus/7.2-t24-fail-a.pdf",
        corrector=correct_natural_language_annotations_undefined,
        context="root/document[0]/pages[0](3 0 obj PDPage)/annots[0](9 0 obj PDLinkAnnot)",
        affected_element_detector=lambda pdf: pdf.pages[0].obj.get("/Annots")[0],
    )
