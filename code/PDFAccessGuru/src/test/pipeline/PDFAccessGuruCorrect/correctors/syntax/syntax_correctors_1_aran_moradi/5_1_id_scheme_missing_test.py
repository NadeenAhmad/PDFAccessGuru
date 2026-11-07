from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi import (
    correct_id_schema_missing,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)


def test_correct_id_schema_missing():
    run_generic_corrector_test(
        rule_id="5-1",
        test_pdf_file="veraPDF_corpus/5-t01-fail-a.pdf",
        corrector=correct_id_schema_missing,
        context=(
            "root/document[0]/metadata[0](3 0 obj PDMetadata)"
            "/XMPPackage[0]"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/Metadata"),  # type: ignore
    )
