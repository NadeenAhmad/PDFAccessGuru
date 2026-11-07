from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_td_headers_missing,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    run_generic_corrector_test,
)


def test_correct_td_headers_missing():
    """
    Notes for detection: 
    resolve_context is not sufficient; the parent element of the resolved
    element is the affected element.
    """
    run_generic_corrector_test(
        rule_id="7.5-1",
        test_pdf_file="veraPDF_corpus/7.5-t01-fail-a.pdf",
        corrector=correct_td_headers_missing,
        context=(
            "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[1](26 0 obj SETable Table)/K[1](45 0 obj SETR TR)/K[1](33 0 obj SETD TD)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1].get("/K")[1].get("/K")[1]  # type: ignore
    )