from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li import (
    correct_table_specific_elements_missing,
)
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    normalize_kids,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    run_generic_syntax_test,
)


def _first_kid(struct_element):
    """Return the first child of a struct element, whether /K is a single object or an array."""
    kids = normalize_kids(struct_element)
    if not kids:
        raise ValueError("Struct element has no children")
    return kids[0]


def test_correct_table_specific_elements_missing():
    """
    Test for rule 7.2-3: a table contains child elements that are not valid table roles.

    This verifies that the corrector replaces invalid child structure types with valid
    table roles such as TR, THead, TBody, TFoot, or Caption.
    """
    run_generic_syntax_test(
        violation_name="table-specific-elements-missing",
        rule_id="7.2-3",
        test_pdf_file="7.2-t03-fail-a.pdf",
        corrector=correct_table_specific_elements_missing,
        context="root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[0](27 0 obj SETable Table)",
        traverse_pdf_function=lambda pdf: _first_kid(_first_kid(pdf.Root.get("/StructTreeRoot"))),
    )
