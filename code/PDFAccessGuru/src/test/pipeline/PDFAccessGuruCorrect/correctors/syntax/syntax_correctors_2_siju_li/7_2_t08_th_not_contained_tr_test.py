import pikepdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li import (
    correct_th_not_contained_tr,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    generate_resource_path,
    run_generic_syntax_test,
)


def test_correct_th_not_contained_tr():
    """
    Test for rule 7.2-8: TH (table header) element is not contained in TR.
    
    This test verifies that the corrector moves the TH element into a TR.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t08-fail-a.pdf")

    with pikepdf.open(pdf_path) as pdf:
        element = pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[0].get("/K")[0] #type: ignore
        print("Objgen:", element.objgen)
        print("Keys:", list(element.keys()))
        print("/S:", element.get("/S"))
        print("/P:", element.get("/P"))
        print("/P /S:", element.get("/P").get("/S") if element.get("/P") else None) #type: ignore

    run_generic_syntax_test(
    violation_name="th-not-contained-tr",
    rule_id="7.2-8",
    test_pdf_file="7.2-t08-fail-a.pdf",
    corrector=correct_th_not_contained_tr,
    context="root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[0](26 0 obj SETable Table)/K[0](42 0 obj SETHead THead)/K[0](29 0 obj SETH TH)",
    traverse_pdf_function=lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[0].get("/K")[0] #type: ignore
    )
