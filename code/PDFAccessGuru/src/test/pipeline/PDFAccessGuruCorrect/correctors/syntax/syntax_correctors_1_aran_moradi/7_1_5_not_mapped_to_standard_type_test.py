from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi import (
    correct_not_mapped_to_standard_type,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)


def test_correct_not_mapped_to_standard_type():
    run_generic_corrector_test(
        rule_id="7.1-5",
        test_pdf_file="veraPDF_corpus/7.1-t05-fail-a.pdf",
        corrector=correct_not_mapped_to_standard_type,
        context=(
            "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)"
            "/K[0](19 0 obj SEDocument Document)"
            "/K[1](35 0 obj SENonStandard Standard)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot")  # type: ignore
            .get("/K").get("/K")[1],  # type: ignore
    )
