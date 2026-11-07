from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart import (
    correct_li_not_contained_l,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
)


def test_correct_li_not_contained_l():
    """
    Notes for detection: 
    resolve_context is not sufficient; the parent element of the resolved
    element is the affected element.
    """
    run_generic_corrector_test(
        rule_id="7.2-17",
        test_pdf_file="veraPDF_corpus/7.2-t17-fail-a.pdf",
        corrector=correct_li_not_contained_l,
        context=(
            "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0]"
            "(15 0 obj SEDocument Document)/K[1](27 0 obj SELI LI)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot")\
            .get("/K"),  # type: ignore
    )
