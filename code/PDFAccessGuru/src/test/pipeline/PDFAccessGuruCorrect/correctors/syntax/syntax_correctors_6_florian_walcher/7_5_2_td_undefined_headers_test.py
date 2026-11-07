from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_td_undefined_headers,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    run_generic_corrector_test,
)


def test_correct_td_undefined_headers():
    """
    Notes for detection: 
    resolve_context is not sufficient; the parent element of the resolved
    element is the affected element.
    """
    run_generic_corrector_test(
        rule_id="7.5-2",
        test_pdf_file="veraPDF_corpus/7.5-t02-fail-a.pdf",
        corrector=correct_td_undefined_headers,
        context=(
            "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](16 0 obj SEDocument Document)/K[1](29 0 obj SETable Table)/K[1](50 0 obj SETR TR)/K[1](36 0 obj SETD TD)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1].get("/K")[1].get("/K")[1] # type: ignore
    )