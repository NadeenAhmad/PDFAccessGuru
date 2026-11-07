from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
    correct_id_note_tag_non_unique,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.test_utils import (
    run_generic_corrector_test,
)


def test_correct_id_note_tag_non_unique():
    """
    Notes for detection: 
    
    """
    run_generic_corrector_test(
        rule_id="7.9-2",
        test_pdf_file="veraPDF_corpus/7.9-t02-fail-a.pdf",
        corrector=correct_id_note_tag_non_unique,
        context=(
            "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](21 0 obj SEDocument Document)/K[3](33 0 obj SENote Note)"
        ),
        affected_element_detector=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[3] # type: ignore
    )