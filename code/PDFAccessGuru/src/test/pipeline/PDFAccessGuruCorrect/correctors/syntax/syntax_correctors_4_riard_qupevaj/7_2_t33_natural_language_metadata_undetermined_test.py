from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import (
    correct_natural_language_metadata_undetermined,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.test_utils import (
    run_generic_corrector_test,
)


def test_correct_natural_language_metadata_undetermined():
    run_generic_corrector_test(
        rule_id="7.2-33",
        test_pdf_file="veraPDF_corpus/7.2-t33-fail-a.pdf",
        corrector=correct_natural_language_metadata_undetermined,
        context="root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]/Properties[6](http://purl.org/dc/elements/1.1/ - dc:title)",
        affected_element_detector=lambda pdf: pdf.Root.get("/Metadata"),
    )
