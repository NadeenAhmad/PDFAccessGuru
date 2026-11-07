from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import (
    correct_natural_language_alt_attribute_undefined,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.test_utils import (
    run_generic_corrector_test,
)


def test_correct_natural_language_alt_attribute_undefined():
    run_generic_corrector_test(
        rule_id="7.2-22",
        test_pdf_file="veraPDF_corpus/7.2-t22-fail-a.pdf",
        corrector=correct_natural_language_alt_attribute_undefined,
        context="root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[1](26 0 obj SEFigure Figure)",
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1],
    )
