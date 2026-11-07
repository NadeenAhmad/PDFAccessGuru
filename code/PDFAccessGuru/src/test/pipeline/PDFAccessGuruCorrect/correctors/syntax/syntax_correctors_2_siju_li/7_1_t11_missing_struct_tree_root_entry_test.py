from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li import (
    correct_missing_struct_tree_root_entry,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    run_generic_syntax_test,
)


def test_correct_missing_struct_tree_root_entry():
    """
    Test for rule 7.1-11: /StructTreeRoot is missing from the document catalog.

    This verifies that the corrector creates a valid structure tree root and marks the
    document as tagged.
    """
    run_generic_syntax_test(
        violation_name="missing-struct-tree-root-entry",
        rule_id="7.1-11",
        test_pdf_file="7.1-t11-fail-a.pdf",
        corrector=correct_missing_struct_tree_root_entry,
        context="root/document[0]",
        traverse_pdf_function=lambda pdf: pdf,
    )
