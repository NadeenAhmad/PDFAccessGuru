import pytest
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi import (
    correct_circular_mapping_exists,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)


def test_correct_circular_mapping_exists():
    #TODO: Fix implement corrector "correct_circular_mapping_exists"
    pytest.skip("Corrector implementation is not correct!")
    run_generic_corrector_test(
        rule_id="7.1-6",
        test_pdf_file="veraPDF_corpus/7.1-t06-fail-a.pdf",
        corrector=correct_circular_mapping_exists,
        context=(
            "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)"
            "/K[0](22 0 obj SEDocument Document)"
            "/K[2](38 0 obj SEL L)"
            "/K[0](56 0 obj SELI LI)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot")  # type: ignore
            .get("/RoleMap"),  # type: ignore
    )
