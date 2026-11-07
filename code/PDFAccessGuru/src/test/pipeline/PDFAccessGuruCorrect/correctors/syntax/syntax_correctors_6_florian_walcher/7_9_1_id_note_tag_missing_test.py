from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_id_note_tag_missing,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    run_generic_corrector_test,
)


def test_correct_id_note_tag_missing():
    """
    Notes for detection: 
    
    """
    run_generic_corrector_test(
        rule_id="7.9-1",
        test_pdf_file="veraPDF_corpus/7.9-t01-fail-a.pdf",
        corrector=correct_id_note_tag_missing,
        context=(
            "root/document[0]/StructTreeRoot[0](8 0 obj PDStructTreeRoot)/K[0](21 0 obj SEDocument Document)/K[1](33 0 obj SENote Note)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1] # type: ignore
    )