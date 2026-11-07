from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi import (
    correct_tagged_content_inside_artifact,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)


def test_correct_tagged_content_inside_artifact():
    run_generic_corrector_test(
        rule_id="7.1-2",
        test_pdf_file="veraPDF_corpus/7.1-t02-fail-a.pdf",
        corrector=correct_tagged_content_inside_artifact,
        context=(
            "root/document[0]/pages[0](9 0 obj PDPage)"
            "/contentStream[0](40 0 obj PDSemanticContentStream)"
            "/content[1]/contentItem[0]"
        ),
        affected_element_detector=lambda pdf: pdf.pages[0],  # type: ignore
    )
