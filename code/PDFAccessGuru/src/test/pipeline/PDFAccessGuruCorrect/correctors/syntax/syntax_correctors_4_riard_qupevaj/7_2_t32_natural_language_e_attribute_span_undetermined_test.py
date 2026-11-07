from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import (
    correct_natural_language_e_attribute_span_undetermined,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.test_utils import (
    run_generic_corrector_test,
)


def test_correct_natural_language_e_attribute_span_undetermined():
    run_generic_corrector_test(
        rule_id="7.2-32",
        test_pdf_file="veraPDF_corpus/7.2-t32-fail-a.pdf",
        corrector=correct_natural_language_e_attribute_span_undetermined,
        context="root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/content[1]{mcid:0}/contentItem[0]{mcid:0}",
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/ParentTree").get("/Nums")[1][0],
    )
