import pytest
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_annotation_artifact_not_nested,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    run_generic_corrector_test,
)


def test_correct_annotation_artifact_not_nested():
    """
    Notes for detection: 
    
    """

    run_generic_corrector_test(
        rule_id="7.18.1-1",
        test_pdf_file="veraPDF_corpus/7.18.1-t01-fail-a.pdf",
        corrector=correct_annotation_artifact_not_nested, # type: ignore
        context=(
            "root/document[0]/pages[0](37 0 obj PDPage)/annots[0](31 0 obj PDMarkupAnnot)"
        ),
        affected_element_detector=lambda pdf: pdf.pages[0].obj.get("/Annots")[0] # type: ignore
    )