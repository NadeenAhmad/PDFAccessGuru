from test.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.test_utils import (
    generate_resource_path, 
    run_generic_resolve_context_test
)


###
# Diverse methods for page traversal verification
#
# Test cases for verifying that there is no difference between traversing a PDFs pages via: 
# (1) pikepdf element pdf.pages[INDEX].obj[...]
# (2) traversing multiple /Pages elements under pdf.Root.get("/Pages").get("/Kids")[INDEX][...]
###

def test_resolve_context_page_traversal_with_page_hierarchy() :
    """
    Tests weather resolve_context can find an /Annots element in a pdf file 
    with pages that are structured in a hierarchical manner instead of a flat array.

    Compares to a manual traversal of the hierarchical structure of the pages.
    """
    pdf_path = generate_resource_path("ProfPDFs/10357-EcoRZ.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Pages").get("/Kids")[7].get("/Kids")[2].get("/Kids")[3].get("/Annots")[0]
    run_generic_resolve_context_test(
        pdf_path, 
        traverse_pdf_function, 
        "7.18.1-2", 
        "root/document[0]/pages[188](1408 0 obj PDPage)/annots[0](8311 0 obj PDLinkAnnot)"
    )

def test_resolve_context_page_traversal_with_global_pages_element() :
    """
    Tests weather resolve_context can find an /Annots element in a pdf file 
    with pages that are structured in a hierarchical manner instead of a flat array.

    Compares to the /Annots element retrieved by directly accessing pdf.pages[INDEX].obj.
    """
    pdf_path = generate_resource_path("ProfPDFs/10357-EcoRZ.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[188].obj.get("/Annots")[0]
    run_generic_resolve_context_test(
        pdf_path, 
        traverse_pdf_function, 
        "7.18.1-2", 
        "root/document[0]/pages[188](1408 0 obj PDPage)/annots[0](8311 0 obj PDLinkAnnot)"
    )

def test_resolve_context_page_traversal_with_page_hierarchy_2() :
    """
    Tests weather resolve_context can find a page element itself in a pdf file 
    with pages that are structured in a hierarchical manner instead of a flat array.

    Compares to a manual traversal of the hierarchical structure of the pages.
    """
    pdf_path = generate_resource_path("ProfPDFs/10357-EcoRZ.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Pages").get("/Kids")[0].get("/Kids")[2].get("/Kids")[4]
    run_generic_resolve_context_test(
        pdf_path, 
        traverse_pdf_function, 
        "7.1-2", 
        "root/document[0]/pages[14](37 0 obj PDPage)/contentStream[0](38 0 obj PDSemanticContentStream)/content[38]"
    )

def test_resolve_context_page_traversal_with_global_pages_element_2() :
    """
    Tests weather resolve_context can find a page element itself in a pdf file 
    with pages that are structured in a hierarchical manner instead of a flat array.

    Compares to the page element retrieved by directly accessing pdf.pages[INDEX].obj.
    """
    pdf_path = generate_resource_path("ProfPDFs/10357-EcoRZ.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[14].obj
    run_generic_resolve_context_test(
        pdf_path, 
        traverse_pdf_function, 
        "7.1-2", 
        "root/document[0]/pages[14](37 0 obj PDPage)/contentStream[0](38 0 obj PDSemanticContentStream)/content[38]"
    )




def test_resolve_context_RADGEN_PDF_7_2_20_nested_li_k574() :
    """
    RADGEN_PDF.pdf, rule 7.2-20. Nested LI inside LBody/L under Sect K[574].

    Context path ends at object 4151 0 (SELI LI), reached via
    LI -> LBody -> L -> LI. Mapping of this nested 7.2-20 path currently fails.
    Expected element is identified by object number rather than K-index walk.
    """
    pdf_path = generate_resource_path("ProfPDFs/RADGEN_PDF.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[574].get("/K")[1].get("/K").get("/K")[1].get("/K")[3]
    run_generic_resolve_context_test(
        pdf_path,
        traverse_pdf_function,
        "7.2-20",
        "root/document[0]/StructTreeRoot[0](865 0 obj PDStructTreeRoot)\
        /K[0](866 0 obj SEDocument Document)/K[0](939 0 obj SESect Sect)\
        /K[574](1514 0 obj SEL L)/K[1](4138 0 obj SELI LI)/K[0](4146 0 obj SELBody LBody)\
        /K[0](4147 0 obj SEL L)/K[3](4151 0 obj SELI LI)",
    )

def test_resolve_context_RADGEN_PDF_7_2_20_nested_li_k1252() :
    """
    RADGEN_PDF.pdf, rule 7.2-20. Nested LI inside LBody/L under Sect K[1252].

    Context path ends at object 2512 0 (SELI LI), reached via
    LI -> LBody -> L -> LI. Mapping of this nested 7.2-20 path currently fails.
    Expected element is identified by object number rather than K-index walk.
    """
    pdf_path = generate_resource_path("ProfPDFs/RADGEN_PDF.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[1252].get("/K")[1].get("/K").get("/K")[1].get("/K")[2]
    run_generic_resolve_context_test(
        pdf_path,
        traverse_pdf_function,
        "7.2-20",
        "root/document[0]/StructTreeRoot[0](865 0 obj PDStructTreeRoot)/K[0](866 0 obj SEDocument Document)/K[0](939 0 obj SESect Sect)/K[1252](2191 0 obj SEL L)/K[1](2507 0 obj SELI LI)/K[0](2508 0 obj SELBody LBody)/K[0](2509 0 obj SEL L)/K[2](2512 0 obj SELI LI)",
    )


# End verification diverse page traversal methods