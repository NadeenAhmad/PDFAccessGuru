import pytest

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li import (
    correct_parent_entry_missing,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    run_generic_syntax_test,
)


def test_correct_parent_entry_missing():
    """
    Test for rule 7.1-12: A structure element is missing the /P (parent) entry.
    
    This test verifies that the corrector finds and assigns the correct parent.
    """
    #TODO: Fix implement corrector "correct_parent_entry_missing" when pdf file is available
    pytest.skip("skip, because pdf is not available in the veraPDF corpus")
    run_generic_syntax_test(
        violation_name="parent-entry-missing",
        rule_id="7.1-12",
        test_pdf_file="7.1-t12-fail-a.pdf",
        corrector=correct_parent_entry_missing,
        context="root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)",
        traverse_pdf_function=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[0]  # type: ignore
    )
