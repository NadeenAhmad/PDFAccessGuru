from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li import (
    correct_tbody_element_missing,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    run_generic_syntax_test,
)


def test_correct_tbody_element_missing():
    """
    Test for rule 7.2-6: TBody is not a direct child of Table.
    
    This test verifies that the corrector moves the TBody to be a direct child of Table.
    """
    run_generic_syntax_test(
        violation_name="tbody-element-missing",
        rule_id="7.2-6",
        test_pdf_file="7.2-t06-fail-a.pdf",
        corrector=correct_tbody_element_missing,
        context="root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[0](30 0 obj SETable Table)/K[0](41 0 obj SETBody TBody)",
        traverse_pdf_function=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1] #type: ignore
    )
