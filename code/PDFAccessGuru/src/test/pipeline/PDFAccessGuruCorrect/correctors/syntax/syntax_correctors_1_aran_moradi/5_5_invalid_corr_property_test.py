from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi import (
    correct_invalid_corr_property,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)


def test_correct_invalid_corr_property():
    run_generic_corrector_test(
        rule_id="5-5",
        test_pdf_file="veraPDF_corpus/5-t05-fail-a.pdf",
        corrector=correct_invalid_corr_property,
        context=(
            "root/document[0]/metadata[0](2 0 obj PDMetadata)"
            "/XMPPackage[0]/PDFUAIdentification[0]"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/Metadata"),  # type: ignore
    )
