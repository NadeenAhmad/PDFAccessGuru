import pytest

from test.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.test_utils import generate_resource_path, run_generic_resolve_context_test


### 
# Test cases files 5-1 to 7.1-6 , Author: Aran Moradi
# Problem: Could not resolve ContentStream element
###

def test_resolve_context_verapdf_ua1_example_5t01() :
    """
    Violation: The document metadata stream doesn't contain PDF/UA Identification Schema
    Context path:
    root/document[0]/metadata[0](3 0 obj PDMetadata)/XMPPackage[0]
    Object

    Test case for the pdf file 5-t01-fail-a.pdf.
    Nothing special about this case.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/5-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Metadata")
    run_generic_resolve_context_test(
        pdf_path, 
        traverse_pdf_function, 
        "5-1", 
        "root/document[0]/metadata[0](3 0 obj PDMetadata)/XMPPackage[0]"
    )

def test_resolve_context_verapdf_ua1_example_5t02():
    """
    Violation: The "part" property of the PDF/UA Identification Schema is not 1 for PDF/UA-1 conforming file
    Context path:
    root/document[0]/metadata[0](3 0 obj PDMetadata)/XMPPackage[0]/PDFUAIdentification[0]

    Afflicted element for this test case could not be found by veraPDF.
    step function is failing because PDFUAIdentification is not resolved.
    --> "part" property should be = 1
    """
    pdf_path = generate_resource_path("veraPDF_corpus/5-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Metadata")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "5-2", 
    "root/document[0]/metadata[0](3 0 obj PDMetadata)/XMPPackage[0]/PDFUAIdentification[0]")

def test_resolve_context_verapdf_ua1_example_5t03():
    """
    Violation: Property "part" of the PDF/UA Identification Schema has invalid namespace prefix
    Context path:
    root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]/PDFUAIdentification[0]

    Afflicted element for this test case could not be found by veraPDF, 
    step function is failing because PDFUAIdentification is not resolved.
    --> "part" property uses wrong XML Namespace prefix
    """
    pdf_path = generate_resource_path("veraPDF_corpus/5-t03-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Metadata")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "5-3",
        "root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]/PDFUAIdentification[0]")

def test_resolve_context_verapdf_ua1_example_5t04():
    """
    Violation: Property "amd" of the PDF/UA Identification Schema has invalid namespace prefix
    Context path:
    root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]/PDFUAIdentification[0]

    Afflicted element for this test case could not be found by veraPDF. 
    step function is failing because PDFUAIdentification is not resolved.
    --> "amd" property uses wrong XML Namespace prefix
    """ 
    pdf_path = generate_resource_path("veraPDF_corpus/5-t04-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Metadata")
    run_generic_resolve_context_test(pdf_path, 
                                           traverse_pdf_function, 
                                           "5-4", 
                                           "root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]/PDFUAIdentification[0]"
                                           )

def test_resolve_context_verapdf_ua1_example_5t05():
    """
    Violation: Property "corr" of the PDF/UA Identification Schema has invalid namespace prefix
    Context path:
    root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]/PDFUAIdentification[0]


    Afflicted element for this test case could not be found by veraPDF.
    step function is failing because PDFUAIdentification is not resolved.
    --> "corr" property uses wrong XML Namespace prefix  
    """
    pdf_path = generate_resource_path("veraPDF_corpus/5-t05-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Metadata")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "5-5", 
                                           "root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]/PDFUAIdentification[0]")


def test_resolve_context_verapdf_ua1_example_61t01():
    """
    Violation: A File header does not match the pattern %PDF-1.n, where 'n' is a single digit number between 0 and 7
    PDF for this case is missing.
    """
    pytest.skip("Test not implemented")


def test_resolve_context_verapdf_ua1_example_61t02():
    """
    Violation: MarkInfo dictionary is not present in the document catalog, 
    or Marked entry is set to false or is not present in the MarkInfo dictionary
    PDF for this case is missing.
    """
    pytest.skip("Test not implemented")

def test_resolve_context_verapdf_ua1_example_71t03():
    """
    Violation: Content is neither marked as Artifact nor tagged as real content
    Context path:
    root/document[0]/pages[0](9 0 obj PDPage)/
    contentStream[0](41 0 obj PDSemanticContentStream)/content[0]/contentItem[0]
    
    --> In the contentstream, contents existing outside the BDC/EMC tags
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t03-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.1-3", 
                                           "root/document[0]/pages[0](9 0 obj PDPage)/contentStream[0](41 0 obj PDSemanticContentStream)/content[0]/contentItem[0]")
    

def test_resolve_context_verapdf_ua1_example_71t04():
    """
    Violation: Suspects entry has a value of true
    Context path:
    root 

    Even though the information is in the /MetaInfo dictionary, resolving the root is sufficient.
    --> Suspects property in MetaInfo is set to True, should be false
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t04-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.1-4", "root")

def test_resolve_context_verapdf_ua1_example_71t05():
    """
    Violation: Non-standard structure type is not mapped to a standard type
    Context path:
    root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)
    /K[1](35 0 obj SENonStandard Standard)/StructElem keys=['/P', '/A', '/Pg', '/Type', '/S', '/K']

    Still AssertionError here
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t05-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.1-5", 
                                           "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[1](35 0 obj SENonStandard Standard)")


def test_resolve_context_verapdf_ua1_example_71t06():
    """
    Violation: A circular mapping exists for structure type
    Context path:
    root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](22 0 obj SEDocument Document)/K[2](38 0 obj SEL L)/K[0](56 0 obj SELI LI)

    --> Circular mapping exists for structure types
    Still AssertionError here
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t06-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[2].get("/K")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.1-6", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](22 0 obj SEDocument Document)/K[2](38 0 obj SEL L)/K[0](56 0 obj SELI LI)")


### 
# Test cases files 7.1-7 to 7.2-8, Author: Siju Li
###

# pytest -s -k

def test_resolve_context_verapdf_ua1_example_71t_standard_type_remapped():
    """
    Violation: standard-type-remapped (7.1-7)
    Standard type is remapped.
    Ein bereits definierter PDF-Standardtag wird unzulässig auf einen anderen Typ gemappt.

    Context path: root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](18 0 obj SENonStandard Document)

    Die Verletzung liegt im /RoleMap-Dictionary innerhalb von /StructTreeRoot.
    veraPDF zeigt daher auf /StructTreeRoot als betroffenes Element, da es keinen
    tieferen Strukturknoten für RoleMap-Verletzungen gibt.

    Das aufgelöste Element ist ausreichend als 'affected element', weil die Korrektur
    direkt am /RoleMap-Eintrag in /StructTreeRoot ansetzt.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t07-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.1-7", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](18 0 obj SENonStandard Document)")


def test_resolve_context_verapdf_ua1_example_71t_metadata_key_missing():
    """
    Violation: metadata-key-missing (7.1-8)
    The document catalog dictionary doesn't contain metadata key or metadata stream dictionary
    does not contain either entry Type with value /Metadata or entry Subtype with value /XML.
    Im Dokumentkatalog fehlt ein gültiger XMP-Metadatenstrom.

    Context path: root/document[0]

    The step function should navigate to pdf.Root.get("/Metadata"). However, since the /Metadata
    key is missing entirely in this PDF, pdf.Root.get("/Metadata") returns None.
    Note: the actual element needed for correction would be pdf.Root itself (so that /Metadata
    can be added as a child), but the purpose of this test is to verify that resolve_context
    and the step function are correctly implemented — not to find the correction target.

    NOTE: This test currently fails due to a missing case in the step function
    (name "Metadata" is not handled, only "metadata" and "PDMetadata").
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t08-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.1-8", "root/document[0]")


def test_resolve_context_verapdf_ua1_example_71t_missing_metadata_stream_dc_title():
    """
    Violation: missing-metadata-stream-dc-title (7.1-9)
    Metadata stream does not contain dc:title.
    Die XMP-Metadaten enthalten keinen dokumentbeschreibenden Titel.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t09-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Metadata")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.1-9", "root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]")

def test_resolve_context_verapdf_ua1_example_71t_display_doc_title_false():
    """
    Violation: display-doc-title-false (7.1-10)
    ViewerPreferences dictionary is not present or DisplayDocTitle key is set to false.
    PDF-Viewer sollen den Dokumenttitel anzeigen; diese Einstellung fehlt oder ist deaktiviert.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t10-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.1-10", "root")

def test_resolve_context_verapdf_ua1_example_71t_missing_struct_tree_root_entry():
    """
    Violation: missing-struct-tree-root-entry (7.1-11)
    StructTreeRoot entry is not present in the document catalog.
    Das Dokument hat keinen Wurzelknoten für die logische Tag-Struktur.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t11-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.1-11", "root/document[0]")

def test_find_affected_element_verapdf_ua1_example_71t_parent_entry_missing():
    """
    Violation: parent-entry-missing (7.1-12)
    Parent entry is not present in the document catalog.
    Das Dokument hat keinen übergeordneten Eintrag im Dokumentkatalog.

    PDF for this case is missing.
    """
    pytest.skip("Test not implemented")

def test_resolve_context_verapdf_ua1_example_72t_natural_language_undefined():
    """
    Violation: natural-language-undefined (7.2-2)
    Natural language in the Outline entries cannot be determined.
    Für Lesezeichen/Gliederungseinträge kann keine natürliche Sprache bestimmt werden.

    Context path: root/document[0]/Outlines[0](outline 13 0)

    Resolving leads to the /Outlines dictionary. The violation is that no natural language
    can be determined for the outline entries because no /Lang tag is set at document level.
    Compare also test_resolve_context_verapdf_ua1_example_72t02 which covers the same
    PDF and violation.

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Outlines")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-2", "root/document[0]/Outlines[0](outline 13 0)")

def test_resolve_context_verapdf_ua1_example_72t_table_specific_elements_missing():
    """
    Violation: table-specific-elements-missing (7.2-3)
    Table element contains element(s) instead of TR, THead, TBody, TFoot or Caption.
    Ein `Table`-Tag enthält Elemente, die laut PDF-Strukturmodell dort nicht hingehören.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t03-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-3", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[0](27 0 obj SETable Table)")

def test_resolve_context_verapdf_ua1_example_72t_tr_element_missing():
    """
    Violation: tr-element-missing (7.2-4)
    TR element not contained in Table, THead, TBody or TFoot element.
    Eine Tabellenzeile steht nicht direkt in einer zulässigen Tabellenstruktur.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t04-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-4", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[0](26 0 obj SETR TR)")

def test_resolve_context_verapdf_ua1_example_72t_thead_element_missing():
    """
    Violation: thead-element-missing (7.2-5)
    THead element not contained in Table element.
    Ein Tabellenkopfbereich steht nicht direkt unter `Table`.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t05-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-5", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[0](30 0 obj SETHead THead)")

def test_resolve_context_verapdf_ua1_example_72t_tbody_element_missing():
    """
    Violation: tbody-element-missing (7.2-6)
    TBody element not contained in Table element.
    Ein Tabellenkörperbereich steht nicht direkt unter `Table`.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t06-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-6", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[1](31 0 obj SETBody TBody)")

def test_resolve_context_verapdf_ua1_example_72t_tfoot_element_missing():
    """
    Violation: tfoot-element-missing (7.2-7)
    TFoot element not contained in Table element.
    Ein Tabellenfußbereich steht nicht direkt unter `Table`.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t07-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-7", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[1](27 0 obj SETFoot TFoot)")

def test_resolve_context_verapdf_ua1_example_72t_th_not_contained_tr():
    """
    Violation: th-not-contained-tr (7.2-8)
    TH element not contained in TR element.
    Eine Tabellenüberschriftenzelle steht nicht innerhalb einer Tabellenzeile.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t08-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[0].get("/K")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-8", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[0](30 0 obj SETable Table)/K[0](70 0 obj SETHead THead)/K[0](32 0 obj SETH TH)")
    

### 
# Test cases files 7.2-9 to 7.2-21, Author: Robin Hart
###


def test_resolve_context_verapdf_ua1_example_72t09() :
    """
    Context path: root/document[0]
        /StructTreeRoot[0](7 0 obj PDStructTreeRoot)
        /K[0](19 0 obj SEDocument Document)
        /K[0](30 0 obj SETable Table)
        /K[1](47 0 obj SETBody TBody)
        /K[0](34 0 obj SETD TD)

    Comment: Context path was difficult to manually resolve (eg. Obj 47 0 notation helped a lot).
    That is because verapdf is looking for e.g. K[0] inside StructTreeRoot, but there is only a single K element,
    which is not an array but a single element. Our step function handles this case correctly.

    Resolving leads to a element tagged as /TBody, inside is an array of 3 elements, 
    which are the rows of the table (tag should be /TR). The detected violation: one row is tagged as table data (/TD).

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t09-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[1].get("/K")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-9", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[0](30 0 obj SETable Table)/K[1](47 0 obj SETBody TBody)/K[0](34 0 obj SETD TD)") 

def test_resolve_context_verapdf_ua1_example_72t10() :
    """
    Context path: root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](15 0 obj SEDocument Document)
        /K[0](26 0 obj SETable Table)
        /K[0](42 0 obj SETHead THead)
        /K[0](49 0 obj SETR TR)

    Comment: Context path was difficult to manually resolve for the same reasons as in test case 7.2-t09.

    Resolving leads to an element tagged as /TR (table row), which contains an array of 3 elements
    which should be tagged as /TH or /TD (table header or table data). Detected violation: one of the elements 
    is instead tagged as /Span.

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t10-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[0].get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-10", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[0](26 0 obj SETable Table)/K[0](42 0 obj SETHead THead)/K[0](49 0 obj SETR TR)") 

def test_resolve_context_verapdf_ua1_example_72t11() :
    """
    Context path: root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)
        /K[0](19 0 obj SEDocument Document)
        /K[0](30 0 obj SETable Table)

    Resolving leads to an element tagged as /Table, which contains an array of 5 elements.
    Detected violation: the first two elements where both tagged as /THead (table head), 
    while only one /THead kid is allowed (others should be tagged e.g. as /TBody or /TFoot).

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t11-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-11", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[0](30 0 obj SETable Table)") 

def test_resolve_context_verapdf_ua1_example_72t12() :
    """
    Context path:  root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)
        /K[0](19 0 obj SEDocument Document)
        /K[0](30 0 obj SETable Table)

    Comment: pdf file is very similar to 7.2-t11.

    Resolving leads to an element tagged as /Table, which contains an array of 5 elements.
    Detected violation: element 2 and 3 are both tagged as /TFoot (table foot), while only 
    one /TFoot kid is allowed.

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t12-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-12", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[0](30 0 obj SETable Table)")

def test_resolve_context_verapdf_ua1_example_72t13() :
    """
    Context path: root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)
        /K[0](19 0 obj SEDocument Document)
        /K[0](30 0 obj SETable Table)

    Comment: pdf file is very similar to 7.2-t11 with one difference: 
    the table body was intentionally left out (elements tagged as /TR are kids of the /Table element 
    instead of being inside a /TBody element).

    Resolving leads to an element tagged as /Table, which contains an array of 5 elements.
    Detected violation: one of these elements is tagged as /TFoot, while none is tagged as 
    /TBody. Instead the others are directly tagged as /TR (or /Caption).

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t13-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-13", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[0](30 0 obj SETable Table)")  

def test_resolve_context_verapdf_ua1_example_72t14() :
    """
    Context path: root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)
        /K[0](19 0 obj SEDocument Document)
        /K[0](30 0 obj SETable Table)

    Comment: pdf file and test case are very similar to 7.2-t13 
    (there is a /THead element instead of /TFoot).

    Resolving leads to an element tagged as /Table, which contains an array of 5 elements.
    Detected violation: one of these elements is tagged as /THead, while none is tagged as 
    /TBody. Instead the others are directly tagged as /TR (or /Caption).

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t14-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-14", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[0](30 0 obj SETable Table)")  

# Comment: 72t15 is not testable, because verapdf corpus does only provide 
# passing files (7.2-t15-pass-a.pdf and 7.2-t15-pass-b.pdf) for this test case, but no failing file.
 
# Comment: 72t16 is not testable, because verapdf corpus does not provide 
# any files for this test case.

def test_resolve_context_verapdf_ua1_example_72t17() :
    """
    Context path: root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](15 0 obj SEDocument Document)
        /K[1](27 0 obj SELI LI)

    Resolving leads to an element tagged as /LI, which for itself is correctly implemented 
    (in particular contains element /Lbl and /LBody). Detected violation: the /LI element is 
    a direct kid of the /Document element, while it should be inside a list element (tag is /L).

    The resolved element is only partly sufficient as 'affected element', because 
    for correction the list root container (tag /L) should be added on the level 
    above of the resolved /LI element and the /LI element should be moved inside of it.
    Correction may still work, by replacing the whole /LI element.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t17-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-17", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[1](27 0 obj SELI LI)")  

def test_resolve_context_verapdf_ua1_example_72t18() :
    """
    Context path: root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](15 0 obj SEDocument Document)
        /K[1](27 0 obj SELBody LBody)

    Comment: Context path is similar to 7.2-t17 but actual tag tree is different. 
    It is noticeable that a correct implemented /L element exists on the same level 
    as the affected /LBody element.

    Resolving leads to an element tagged as /LBody. Detected violation: the /LBody element 
    is a direct kid of the /Document element, while it should be inside a list element (tag is /L).

    The resolved element is only partly sufficient as 'affected element', because 
    of the same reasons as in test case 7.2-t17.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t18-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-18", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[1](27 0 obj SELBody LBody)")  

def test_resolve_context_verapdf_ua1_example_72t19() :
    """
    Context path: root
        /document[0]
        /StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](15 0 obj SEDocument Document)
        /K[0](26 0 obj SEL L)

    Comment: "fail-b" was chosen because "fail-a" actually corresponds to 7.2-40 
    (see test for that, error by verapdf corpus).

    Resolving leads to an element tagged as /L. Detected violation: child with 
    index 1 is tagged as /Span, which is not allowed inside /L 
    (only /LI, /Caption or /L elements are allowed as kids of /L).

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t19-fail-b.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-19", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[0](26 0 obj SEL L)")  

def test_resolve_context_verapdf_ua1_example_72t20() :
    """
    Context path: root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](15 0 obj SEDocument Document)
        /K[0](26 0 obj SEL L)
        /K[1](42 0 obj SELI LI)

    Resolving leads to an element tagged as /LI, which contains two elements. 
    It is expected that one of these elements is tagged as /Lbl and the other 
    one is tagged as /LBody. Detected violation: one of the elements is tagged 
    as /Span instead of /Lbl.

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t20-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-20", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[0](26 0 obj SEL L)/K[1](42 0 obj SELI LI)")  

def test_resolve_context_verapdf_ua1_example_72t21() :
    """
    Context path: root/document[0]/StructTreeRoot[0](5 0 obj PDStructTreeRoot)
        /K[0](11 0 obj SEDocument Document)
        /K[0](20 0 obj SEHn H1)

    Comment: This case brings up the same problem we have in 72t02 
    (discussed on sprint meeting after sprint 2): the missing /Lang tag 
    inside the /Root element ('top level /Lang tag'). Source of this analysis:
    Compare file '7.2-t21-fail-a.pdf' with '7.2-t21-pass-a.pdf'.

    Resolving leads to an element tagged as /H1 (headline) which contains an /ActualText tag.
    Detected violation: no /Lang tag was found inside the resolved element nor in any of
    its parent elements (in particular not in the /Root element).

    The resolved element is not sufficient as 'affected element' (see above). But:
    May not be a problem for correction.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t21-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-21", "root/document[0]/StructTreeRoot[0](5 0 obj PDStructTreeRoot)/K[0](11 0 obj SEDocument Document)/K[0](20 0 obj SEHn H1)")  



### 
# Test cases files 7.2-22 to 7.2-34, Author: Riard Qupevaj 
###


def test_resolve_context_verapdf_ua1_example_72t22() :
    """
    Context path:
    root/document[0]/StructTreeRoot[0]/K[0]/K[1]

    Comment:
    In this file, violation index 0 points into StructTreeRoot. The Outlines
    context for this test starts at violation index 1.

    Detected violation:
    Rule 7.2-22 is reported on a StructElem containing Alt text.

    Assessment:
    Resolving to the specific StructElem is required for rule-accurate mapping.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t22-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-22", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[1](26 0 obj SEFigure Figure)")


def test_resolve_context_verapdf_ua1_example_72t23() :
    """
    Context path:
    root/document[0]/StructTreeRoot[0]/K[0]/K[1]

    Comment:
    Violation index 0 points to page content (mcid path). For this test we
    intentionally validate the outlines mapping at index 1.

    Detected violation:
    Rule 7.2-23 is reported on a StructElem containing E attribute text.

    Assessment:
    Resolving to the specific StructElem is required for rule-accurate mapping.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t23-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1]
    run_generic_resolve_context_test(
        pdf_path, traverse_pdf_function, "7.2-23", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](14 0 obj SEDocument Document)/K[1](24 0 obj SEP P)") 


def test_resolve_context_verapdf_ua1_example_72t24() :
    """
    Context path:
    root/document[0]/pages[0]/annots[0]

    Comment:
    This rule points to annotation contents on the page.

    Detected violation:
    Rule 7.2-24 is detected on annotation language.

    Assessment:
    Mapping to the concrete annotation object is required.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t24-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Annots")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-24", "root/document[0]/pages[0](3 0 obj PDPage)/annots[0](9 0 obj PDLinkAnnot)") 


def test_resolve_context_verapdf_ua1_example_72t25() :
    """
    Context path:
    root/document[0]/AcroForm[0]/formFields[0]

    Comment:
    This rule points directly to a form field under AcroForm.

    Detected violation:
    Rule 7.2-25 is reported for TU language in form fields.

    Assessment:
    Mapping to the concrete field object is required.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t25-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/AcroForm").get("/Fields")[0]
    run_generic_resolve_context_test(
        pdf_path, traverse_pdf_function, "7.2-25", "root/document[0]/AcroForm[0]/formFields[0](3 0 obj PDTextField)")


def test_resolve_context_verapdf_ua1_example_72t26() :
    """
    Context path:
    root/document[0]/StructTreeRoot[0]/K[0]/K[0]/K[1]

    Comment:
    StructTreeRoot./K is a single object in this file (not an array). This is a
    structural edge case compared to many other corpus PDFs.

    Detected violation:
    Rule 7.2-26 is detected on a TOCI element in the structure tree.

    Assessment:
    Resolving to the specific StructElem (K[1]) is precise and sufficient.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t26-fail-a.pdf")
    traverse_pdf_function = lambda pdf: (
        pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[0].get("/K")[1]
    )
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-26", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](18 0 obj SEDocument Document)/K[0](31 0 obj SENonStruct NonStruct)/K[1](55 0 obj SETOCI TOCI)") 


def test_resolve_context_verapdf_ua1_example_72t27() :
    """
    Context path:
    root/document[0]/StructTreeRoot[0]/K[0]/K[0]

    Comment:
    Similar to 7.2-t26, but the target is the parent TOC element itself.

    Detected violation:
    Rule 7.2-27 is raised on the TOC StructElem.

    Assessment:
    Returning that exact StructElem is sufficient for rule-specific handling.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t27-fail-c.pdf")
    traverse_pdf_function = lambda pdf: (
        pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[0]
    )
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-27", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](18 0 obj SEDocument Document)/K[0](31 0 obj SETOC TOC)") 


def test_resolve_context_rule_72t28() :
    """
    Context path:
    root/document[0]/StructTreeRoot[0]/K[0]/K[0]

    Comment:
    This test uses a generated PDFAccessGuru corpus file because the original
    veraPDF corpus does not provide a dedicated 7.2-t28 fail file.

    Detected violation:
    Rule 7.2-28 (TOC contains Caption child not as first one).

    Assessment:
    Resolving to the TOC StructElem is sufficient as affected element for this
    rule.
    """
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t28-fail-a.pdf")
    traverse_pdf_function = lambda pdf: (
        pdf.Root.get("/StructTreeRoot").get("/K")[1]
    )
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-28", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[1](19 0 obj SETOC TOC)")

def test_resolve_context_verapdf_ua1_example_72t29() :
    """
    Context path:
    root/document[0]/Lang[0]

    Comment:
    This case targets the catalog language entry directly, without navigating
    into outlines or structure elements.

    Detected violation:
    Rule 7.2-29 is reported because document natural language metadata is
    missing/invalid at root level.

    Assessment:
    Resolving to /Lang is sufficient because fixes are applied at catalog root.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t29-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Lang")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-29", "root/document[0]/Lang[0]") 


def test_resolve_context_verapdf_ua1_example_72t30() :
    """
    Context path:
    root/document[0]/pages[0]/contentStream[0]/content[..]/contentItem[..]

    Comment:
    This rule points into content stream semantics for Span content.

    Detected violation:
    Rule 7.2-30 is detected on ActualText span semantics.

    Assessment:
    In current resolver design, content-level paths map back to the containing page.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t30-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-30", "root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/content[1]{mcid:0}/contentItem[0]{mcid:0}") 


def test_resolve_context_verapdf_ua1_example_72t31() :
    """
    Context path:
    root/document[0]/pages[0]/contentStream[0]/content[...]/contentItem[...]

    Comment:
    veraPDF points into semantic content items. pikepdf does not expose these
    as separate objects, so resolver intentionally maps back to page object.

    Detected violation:
    Rule 7.2-31 is reported for content-level semantics on page 0.

    Assessment:
    Returning page 0 object is sufficient for current fix strategy.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t31-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-31", "root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/content[1]{mcid:0}/contentItem[0]{mcid:0}") 


def test_resolve_context_verapdf_ua1_example_72t32() :
    """
    Context path:
    root/document[0]/pages[0]/contentStream[0]/content[...]/contentItem[...]

    Comment:
    Same resolver strategy as 7.2-t31: content-node segments are folded to the
    containing page object.

    Detected violation:
    Rule 7.2-32 is detected on page-level semantic content.

    Assessment:
    Page 0 is an adequate affected element for downstream correction.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t32-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-32", "root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/content[1]{mcid:0}/contentItem[0]{mcid:0}") 


def test_resolve_context_verapdf_ua1_example_72t33() :
    """
    Context path:
    root/document[0]/metadata[0]/XMPPackage[0]/Properties[6](http://...)

    Comment:
    veraPDF drills into parsed XMP properties. In pikepdf these are not exposed
    as separate objects; resolver keeps metadata stream as target.

    Detected violation:
    Rule 7.2-33 is raised on metadata language/title semantics.

    Assessment:
    /Metadata stream is sufficient as affected element for metadata correction.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t33-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Metadata")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-33", "root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]/Properties[6](http://purl.org/dc/elements/1.1/ - dc:title)")

def test_resolve_context_verapdf_ua1_example_72t34() :
    """
    Context path:
    root/document[0]/pages[0]/contentStream[0]/content[..]/contentItem[..]

    Comment:
    Multiple 7.2-34 hits exist on page content items. One representative hit
    is selected by rule_id and contentStream context.

    Detected violation:
    Rule 7.2-34 is detected on natural-language-in-page-content checks.

    Assessment:
    In current resolver design, content-level paths map back to the containing page.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t34-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-34", "root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/content[1]{mcid:0}/contentItem[0]{mcid:0}") 



### 
# Test cases files 7.2-36 to 7.4.4-3 , Author: Brian Karle
###

def test_resolve_context_verapdf_ua1_example_72t36() :
    """
    Violation: 7.2-36 thead-invalid-elements

    Context path: root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](15 0 obj SEDocument Document)
        /K[0](26 0 obj SETable Table)
        /K[0](42 0 obj SETHead THead)
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t36-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-36", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[0](26 0 obj SETable Table)/K[0](42 0 obj SETHead THead)")


def test_resolve_context_verapdf_ua1_example_72t37() :
    """
    Violation: 7.2-37 tbody-invalid-elements

    Context path: root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](15 0 obj SEDocument Document)
        /K[0](26 0 obj SETable Table)
        /K[1](43 0 obj SETBody TBody)
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t37-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[1] 
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-37", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[0](26 0 obj SETable Table)/K[1](43 0 obj SETBody TBody)")


def test_resolve_context_verapdf_ua1_example_72t38() :
    """
    Violation: 7.2-38 tfoot-invalid-elements

    Context path: root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](15 0 obj SEDocument Document)
        /K[0](26 0 obj SETable Table)
        /K[3](45 0 obj SETFoot TFoot)
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t38-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[3] 
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-38", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[0](26 0 obj SETable Table)/K[3](45 0 obj SETFoot TFoot)")


def test_resolve_context_verapdf_ua1_example_72t39() :
    """
    Violation: 7.2-39 table-several-captions

    Context path: root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)
        /K[0](14 0 obj SEDocument Document)
        /K[0](24 0 obj SETable Table)
    """
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t39-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-39", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](14 0 obj SEDocument Document)/K[0](24 0 obj SETable Table)")



def test_resolve_context_verapdf_ua1_example_72t40() :
    """
    IMPORTANT: this is a test added by Robin Hart. Because file 
    7.2-t19-fail-a.pdf does include a violation of rule 7.2-40.
    (I think it is an error with the verapdf corpus.)

    Context path: root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](15 0 obj SEDocument Document)
        /K[0](26 0 obj SEL L)

    Resolving leads to an element tagged as /L, which contains an array of 5 elements. 
    The first four elements are tagged as /LI. Detected violation: only the last element 
    is tagged as /Caption, while a /Caption element is only allowed as the first kid.

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t19-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-40", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[0](26 0 obj SEL L)")  


def test_resolve_context_verapdf_ua1_example_72t41() :
    """
    Violation: 7.2-41 table-columns-different-number-rows

    Comment by Robin Hart: verapdf actually detects the wrong clause here: 7.2-42 instead of 7.2-41. 
    The file may not be usefull!
    
    Context path: root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](12 0 obj SEDocument Document)
        /K[1](19 0 obj SETable Table)
    
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t41-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-42", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](12 0 obj SEDocument Document)/K[1](19 0 obj SETable Table)")


def test_resolve_context_verapdf_ua1_example_72t42() :
    """
    Violation: 7.2-42 table-rows-span-different-number-columns

    Context path: root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](14 0 obj SEDocument Document)
        /K[0](24 0 obj SETable Table)
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t42-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-42", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](14 0 obj SEDocument Document)/K[0](24 0 obj SETable Table)")


def test_resolve_context_verapdf_ua1_example_72t43() :
    """
    Violation: 7.2-43 table-rows-span-different-number-columns-02

    Context path: root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)
        /K[0](14 0 obj SEDocument Document)
        /K[0](24 0 obj SETable Table)
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t43-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.2-43", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](14 0 obj SEDocument Document)/K[0](24 0 obj SETable Table)")


def test_resolve_context_verapdf_ua1_example_73t01() :
    """
    Violation: 7.3-1 figure-structure-alternate-description-missing

    Context path: root/document[0]/StructTreeRoot[0](17 0 obj PDStructTreeRoot)
        /K[0](23 0 obj SEDocument Document)
        /K[1](21 0 obj SEP P)
        /K[0](20 0 obj SEFigure Figure)
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.3-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1].get("/K")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.3-1", "root/document[0]/StructTreeRoot[0](17 0 obj PDStructTreeRoot)/K[0](23 0 obj SEDocument Document)/K[1](21 0 obj SEP P)/K[0](20 0 obj SEFigure Figure)")


def test_resolve_context_verapdf_ua1_example_742t01() :
    """
    Violation: 7.4.2-1 heading-level-skipped

    Context path: root/document[0]/StructTreeRoot[0](20 0 obj PDStructTreeRoot)
        /K[0](27 0 obj SEDocument Document)
        /K[1](23 0 obj SEHn H2)
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.4.2-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.4.2-1", "root/document[0]/StructTreeRoot[0](20 0 obj PDStructTreeRoot)/K[0](27 0 obj SEDocument Document)/K[1](23 0 obj SEHn H2)")


def test_resolve_context_verapdf_ua1_example_744t01() :
    """
    Violation: 7.4.4-1 node-more-one-h-tag

    Context path: root/document[0]/StructTreeRoot[0](18 0 obj PDStructTreeRoot)
        /K[0](19 0 obj SEDocument Document)
        /K[0](25 0 obj SESect Sect)
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.4.4-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.4.4-1", "root/document[0]/StructTreeRoot[0](18 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[0](25 0 obj SESect Sect)")


def test_resolve_context_verapdf_ua1_example_744t02() :
    """
    Violation: 7.4.4-2 document-uses-h-h#-tags

    Context path: root/document[0]/StructTreeRoot[0](20 0 obj PDStructTreeRoot)
        /K[0](21 0 obj SEDocument Document)
        /K[1](28 0 obj SESect Sect)
        /K[0](25 0 obj SEH H)
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.4.4-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1].get("/K")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.4.4-2", "root/document[0]/StructTreeRoot[0](20 0 obj PDStructTreeRoot)/K[0](21 0 obj SEDocument Document)/K[1](28 0 obj SESect Sect)/K[0](25 0 obj SEH H)")


def test_resolve_context_verapdf_ua1_example_744t03() :
    """
    Violation: 7.4.4-3 document-uses-hn-h-tags

    Context path: root/document[0]/StructTreeRoot[0](18 0 obj PDStructTreeRoot)
        /K[0](19 0 obj SEDocument Document)
        /K[1](26 0 obj SESect Sect)
        /K[0](23 0 obj SEHn H1)
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.4.4-t03-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1].get("/K")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.4.4-3", "root/document[0]/StructTreeRoot[0](18 0 obj PDStructTreeRoot)/K[0](19 0 obj SEDocument Document)/K[1](26 0 obj SESect Sect)/K[0](23 0 obj SEHn H1)")



### 
# Test cases files 7.5-7 to 7.18.1-3, Author: Florian walcher
###

# pytest -s -k "test_resolve_context_verapdf_ua1_example_71t_standard_type_remapped"

def test_resolve_context_verapdf_ua1_example_75t01() :
    """
    td-headers-missing

    Context path: root/document[0]
    /StructTreeRoot[0](6 0 obj PDStructTreeRoot)
    /K[0](15 0 obj SEDocument Document)
    /K[1](26 0 obj SETable Table)
    /K[1](45 0 obj SETR TR)
    /K[1](33 0 obj SETD TD)

    Context path does not lead to the missing TH element, but to the first TD element below the TH element. The TH element's /Scope is missing "/Row" and can be found at pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1].get("/K")[1].get("/K")[0].get("/A")[1].

    The resolved element is partially sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.5-t01-fail-b.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1].get("/K")[1].get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.5-1", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[1](26 0 obj SETable Table)/K[1](45 0 obj SETR TR)/K[1](33 0 obj SETD TD)")

def test_resolve_context_verapdf_ua1_example_75t02() :
    """
    td-undefined-headers

    Context path: root/document[0]
    /StructTreeRoot[0](6 0 obj PDStructTreeRoot)
    /K[0](16 0 obj SEDocument Document)
    /K[1](29 0 obj SETable Table)
    /K[1](50 0 obj SETR TR)
    /K[1](36 0 obj SETD TD)

    Comment: Similar to 7.5-01, the Context path does not lead to the missing TH element, but to the first TD element below the TH element. The TH element's /Scope is missing "/Row" and can be found at pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1].get("/K")[1].get("/K")[0].get("/A")[1].
    Furthermore, the TD element references an undefined header at pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1].get("/K")[1].get("/K")[1].get("/A")[1].get("/Headers")[0].

    The resolved element is partially sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.5-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1].get("/K")[1].get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.5-2", "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](16 0 obj SEDocument Document)/K[1](29 0 obj SETable Table)/K[1](50 0 obj SETR TR)/K[1](36 0 obj SETD TD)")

def test_resolve_context_verapdf_ua1_example_77t01() :
    """
    formula-structure-no-alternative-description

    Context path: root/document[0]
    /StructTreeRoot[0](2 0 obj PDStructTreeRoot)
    /K[0](9 0 obj SEDocument Document)
    /K[1](18 0 obj SEFormula Formula)

    Missing /Alt attribute of the formula structure element would be found at pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1].
    The first /K is notably NOT an array, even if the context path suggests otherwise.

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.7-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.7-1", "root/document[0]/StructTreeRoot[0](2 0 obj PDStructTreeRoot)/K[0](9 0 obj SEDocument Document)/K[1](18 0 obj SEFormula Formula)")

def test_resolve_context_verapdf_ua1_example_79t01() :
    """
    id-note-tag-missing

    Context path: root/document[0]/
    StructTreeRoot[0](8 0 obj PDStructTreeRoot)
    /K[0](21 0 obj SEDocument Document)
    /K[1](33 0 obj SENote Note)

    Comment: The object is missing /ID: Note, which is required for the Note structure element. 

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.9-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[1]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.9-1", "root/document[0]/StructTreeRoot[0](8 0 obj PDStructTreeRoot)/K[0](21 0 obj SEDocument Document)/K[1](33 0 obj SENote Note)")

def test_resolve_context_verapdf_ua1_example_79t02() :
    """
    id-note-tag-non-unique

    Context path: root/document[0]
    /StructTreeRoot[0](7 0 obj PDStructTreeRoot)
    /K[0](21 0 obj SEDocument Document)
    /K[3](33 0 obj SENote Note)

    Comment: Context path is insufficient, finding the error is more complex. In the passing pdf, /Root/StructTreeRoot/IDTree/Names[1]/P/K[3]/ID is different from /Root/StructTreeRoot/IDTree/Names[1]/ID, while in the failing pdf they are identical. We need to check for uniqueness among notes at different parts of the hierarchy.

    The resolved element is partially sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.9-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K")[0].get("/K")[3]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.9-2", "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](21 0 obj SEDocument Document)/K[3](33 0 obj SENote Note)")

def test_resolve_context_verapdf_ua1_example_710t01() :
    """
    missing-empty-name

    Context path: root/document[0]
    /OCProperties[0](3 0 obj PDOCProperties)
    /D[0]

    Comment: Failing test file a as an empty name entry, while failing test file b has no name entry at all.

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.10-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/OCProperties").get("/D")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.10-1", "root/document[0]/OCProperties[0](3 0 obj PDOCProperties)/D[0]")

def test_resolve_context_verapdf_ua1_example_710t02() :
    """
    present-optional-content-configuration

    Context path: root/document[0]/OCProperties[0](29 0 obj PDOCProperties)/D[0]

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.10-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/OCProperties").get("/D")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.10-2", "root/document[0]/OCProperties[0](29 0 obj PDOCProperties)/D[0]")

def test_resolve_context_verapdf_ua1_example_711t01() :
    """
    f-uf-key-invalid

    Context path: root/EmbeddedFiles[0]

    Comment: What's actually missing is in the test file is Trailer/Root/Names/EmbeddedFiles/Names[1]/F. It's unclear how to reach it with our traverse function.

    Warning: verapdf provided two verapdf violations: 
        - rule_id=7.11-1, context=root/EmbeddedFiles[0]
        - rule_id=7.11-1, context=root/indirectObjects[4](23 0)/directObject[0]
    But the same rule_id for both verapdf violations!
    
    To check: is resolved element sufficient as 'affected element' for both violations?
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.11-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.Names.EmbeddedFiles
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.11-1", "root/EmbeddedFiles[0]")

def test_resolve_context_verapdf_ua1_example_715t01() :
    """
    dynamic-xfa-forms-present

    Context path: root/document[0]
    /AcroForm[0](2 0 obj PDAcroForm)

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.15-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/AcroForm")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.15-1", "root/document[0]/AcroForm[0](2 0 obj PDAcroForm)")

def test_resolve_context_verapdf_ua1_example_716t01() :
    """
    encrypted-file-p-missing

    Context path: root/trailer[0]/
    Encrypt[0](30 0 obj PDEncryption)

    Added by Robin Hart (08.06.2026, 23:00):
    The resolved element is sufficient as 'affected element', because you can directly read out the /P key 
    in the resolved element.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.16-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.trailer.get("/Encrypt")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.16-1", "root/trailer[0]/Encrypt[0](30 0 obj PDEncryption)")

def test_resolve_context_verapdf_ua1_example_7181t01() :
    """
    annotation-artifact-not-nested

    Context path: root/document[0]
    /pages[0](37 0 obj PDPage)
    /annots[0](31 0 obj PDMarkupAnnot)

    Comment: Fail and pass are not directly comparable. 
    Fail uses a highlight annotation on the word "annotation", 
    while pass uses a link to the verapdf github page on the word "link".

    It is unclear if the resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.1-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Annots")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.18.1-1", "root/document[0]/pages[0](37 0 obj PDPage)/annots[0](31 0 obj PDMarkupAnnot)")

def test_resolve_context_verapdf_ua1_example_7181t02() :
    """
    invalid-annotation

    Context path: root/document[0]
    /pages[0](10 0 obj PDPage)
    /annots[0](16 0 obj PDMarkupAnnot)

    Comment: (added by Robin Hart, 08.06.2026, 23:00) This one is very difficult to correct.
    That is because the actual difference between the failing and passing pdf (file a) does not lie inside /pages/annots but inside /StructTreeRoot (more precisely: /StructTreeRoot/K[0]/K[0](Obj 20:0).
    In the failing pdf that element does not have an /Alt tag. In the passing pdf it does have an /Alt tag containing the word "highlight".

    Idea to fix: Look inside the StructTreeRoot. One child of the previously shown element does contain a link to Element "Obj 16:0" (It says "Jump to[...]"). We will have to write a custom search affected element function for this one, which takes this into account.
    It is a possibility to ask Nadeen this one.
    
    The resolved element is NOT sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.1-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Annots")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.18.1-2", "root/document[0]/pages[0](10 0 obj PDPage)/annots[0](16 0 obj PDMarkupAnnot)")

def test_resolve_context_verapdf_ua1_example_7181t03() :
    """
    form-field-missing-alt-entry

    Context path: root/document[0]
    /pages[0](52 0 obj PDPage)
    /annots[0](39 0 obj PDWidgetAnnot)

    Comment: Annots[0] is missing a /TU entry, which is present in the correct version of the pdf.

    The resolved element is sufficient as 'affected element'.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.1-t03-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Annots")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.18.1-3", "root/document[0]/pages[0](52 0 obj PDPage)/annots[0](39 0 obj PDWidgetAnnot)")


##
# Test cases for 7.18.2-1 to 7.21.3.2-1, Author: Marwa Ayache
##
def test_resolve_context_verapdf_ua1_example_7182t01() :
    """
     veraPDF context:
    root/document[0]/pages[0](35 0 obj PDPage)/annots[0](28 0 obj PDTrapNetAnnot)

    The affected element is the annotation dictionary itself.
    In the PDF structure, the first page contains an /Annots array, and its first
    entry has /Subtype /TrapNet.

    Correction idea: may be corrected deterministically by removing the TrapNet annotation and replacing
    it with an allowed annotation subtype.

    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.2-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Annots")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.18.2-1", "root/document[0]/pages[0](35 0 obj PDPage)/annots[0](28 0 obj PDTrapNetAnnot)")

def test_resolve_context_verapdf_ua1_example_7183t01() :
    """
     veraPDF context:
    root/document[0]/pages[0](82 0 obj PDPage)

     The affected element is the page dictionary itself, because /Tabs is a page
    dictionary entry. In this test case, /Tabs is missing completely.

    Related case: in test case b (i.e. 7.18.3-t01-fail-b.pdf)
    the /Tabs key does exist, just with a wrong value.

     The resolved element is sufficient as affected element, because the correction
    can be performed directly on the page dictionary by adding /Tabs /S.

    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.3-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.18.3-1", "root/document[0]/pages[0](82 0 obj PDPage)")

def test_resolve_context_verapdf_ua1_example_7184t01() :
    """
    veraPDF context:
    root/document[0]/pages[0](51 0 obj PDPage)/annots[0](34 0 obj PDWidgetAnnot)

    Detected violation:
    7.18.4-1: A Widget annotation is not nested within a Form tag.


    The resolved element is sufficient for identifying the affected widget annotation,
    because veraPDF reports the concrete /Widget annotation in the page's /Annots array.

    However, the resolved annotation dictionary alone is not sufficient for a complete
    correction. The rule depends on whether the widget annotation is represented in
    the logical structure tree as part of a /Form structure element and not as an
    Artifact. Therefore, an automatic repair would also need to inspect the annotation's
    /StructParent entry (e.g. in the ...-pass-a.pdf test case, /StructParent was greater)

    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.4-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Annots")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.18.4-1", "root/document[0]/pages[0](51 0 obj PDPage)/annots[0](34 0 obj PDWidgetAnnot)")


def test_resolve_context_verapdf_ua1_example_7184t02():
    """
    veraPDF context:
    root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](8 0 obj SEDocument Document)/K[3](10 0 obj SEForm Form)

    Detected violation:
    7.18.4-2: The Form element omits a Role attribute and does not have only
    one child identifying the widget annotation.

    Comment:
    the relevant affected element is the /Form structure element itself,
    not the widget annotation in /Annots.
    The /Form structure element is located under the logical structure tree at:

    /Root -> /StructTreeRoot -> /K -> /K[3]

    That element currently has multiple children in its /K entry, although it
    should contain exactly one child identifying the widget annotation.
    Therefore, resolving the veraPDF context directly to the /Form structure
    element is sufficient for deterministic correction.
    """
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.18.4-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[3]
    run_generic_resolve_context_test(
        pdf_path,
        traverse_pdf_function,
        "7.18.4-2",
        "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](8 0 obj SEDocument Document)/K[3](10 0 obj SEForm Form)",
    )


def test_resolve_context_verapdf_ua1_example_7185t01():
    """
    veraPDF context:
    root/document[0]/pages[0](27 0 obj PDPage)/annots[0](22 0 obj PDLinkAnnot)

    Detected violation:
    7.18.5-1: A Link annotation is not nested within a /Link tag.

    Comment:
    This PDF contains one link annotation on page 0. The annotation has
    /Subtype /Link and is located at page 0 /Annots[0].

    The affected element resolved by veraPDF is the link annotation dictionary
    itself, which is enough to identify which link annotation is affected.
     But the resolved element is not sufficient for a complete correction,
     because fixing the violation requires checking or modifying the annotation's
    relationship to the logical structure tree, especially the /StructParent entry,
    the ParentTree, and the corresponding /Link structure element.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.5-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Annots")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.18.5-1", "root/document[0]/pages[0](27 0 obj PDPage)/annots[0](22 0 obj PDLinkAnnot)")

def test_resolve_context_verapdf_ua1_example_7185t02():
    """
    pdftree src/test/resources/veraPDF_corpus/7.18.3-t01-fail-a.pdf
    veraPDF context:
    root/document[0]/pages[0](30 0 obj PDPage)/annots[0](23 0 obj PDLinkAnnot)

    Detected violation:
    7.18.5-2: A Link annotation does not include an alternate description in the
    /Contents key.

    Comment: In the failing PDF, the link annotation does not contain a /Contents entry.
    In the passing PDF, the same kind of link annotation contains a /Contents
    entry with an alternate description.

    The element resolved by veraPDF is the real affected element, so it is sufficient as
    a correction target, because the required repair can be applied directly to this annotation dictionary
    by adding a suitable /Contents entry.

    !Note: in 7.18.5-t02-fail-b.pdf the /Contents key exists but is just empty.

    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.5-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Annots")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.18.5-2", "root/document[0]/pages[0](30 0 obj PDPage)/annots[0](23 0 obj PDLinkAnnot)")



def test_resolve_context_verapdf_ua1_example_71862t01():
    """
    veraPDF context:
    root/document[0]/pages[0](3 0 obj PDPage)/annots[0](8 0 obj PDScreenAnnot)/A[0]/C[0]

    Detected violation:
    7.18.6.2-1: CT key is missing from the media clip data dictionary.

    Important observation:
    The veraPDF context path ends with /A[0]/C[0], but in the raw PDF object tree
    the media clip data dictionary /C is nested inside the rendition dictionary /R
    of the action dictionary /A.

    Raw PDF path:
    page 0 /Annots[0] -> /A -> /R -> /C

   If resolve_context() cannot resolve this path(returns None), the resolved affected element is
   currently not found by the implementation, even though the target object exists
   in the raw PDF tree. This is why the test fails

    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.6.2-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Annots")[0].get("/A").get("/R").get("/C")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.18.6.2-1", "root/document[0]/pages[0](3 0 obj PDPage)/annots[0](8 0 obj PDScreenAnnot)/A[0]/C[0]")



def test_resolve_context_verapdf_ua1_example_71862t02():
    """
    veraPDF context:
    root/document[0]/pages[0](3 0 obj PDPage)/annots[0](8 0 obj PDScreenAnnot)/A[0]/C[0]

    Detected violation:
    7.18.6.2-2: Alt key is missing from the media clip data dictionary

    Important observation:
    (same issue as the previous test case)
    The veraPDF context path ends with /A[0]/C[0], but in the raw PDF object tree
    the media clip data dictionary /C (inside this key you can find the /Alt key) is nested inside the
    rendition dictionary /R of the action dictionary /A.

    Raw PDF path:
    page 0 /Annots[0] -> /A -> /R -> /C -> /Alt

   If resolve_context() cannot resolve this path(returns None), the resolved affected element is
   currently not found by the implementation, even though the target object exists
   in the raw PDF tree. This is why the test fails

    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.6.2-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Annots")[0].get("/A").get("/R").get("/C")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.18.6.2-2", "root/document[0]/pages[0](3 0 obj PDPage)/annots[0](8 0 obj PDScreenAnnot)/A[0]/C[0]")


#def test_resolve_context_verapdf_ua1_example_7187t01():
#    """
#    note: this rule is not found in the taxonomy nor in the veraPDF
#    Wiki
#    veraPDF context:
#     root/indirectObjects[14](22 0)/directObject[0]
#
#    Detected violation:
#    File attachment annotations (ISO 32000-1:2008, 12.5.6.15)
#    shall conform to all requirements in 7.11.
#
#    Comment:
#    the /indirectObjects key is not present in the PDF structure tree (and after some
#    research, it does not exist in general as a PDF dictionary key). This is an
#    "internal" implementation Detail von veraPDF maybe used to keep track of cross-referenced
#    objects (in this case it makes sense because this violation references to another violation)
#
#    _resolve_context() likely returns None in this case. Therefore, the test fails
#
#    """
#    pdf_path = generate_resource_path("veraPDF_corpus/7.18.7-t01-fail-a.pdf")
#    traverse_pdf_function = lambda pdf: pdf.get_object(22,0)
#    run_generic_resolve_context_test(pdf_path, traverse_pdf_function)

def test_resolve_context_verapdf_ua1_example_7188t01():
    """
    veraPDF context:
    root/document[0]/pages[0](7 0 obj PDPage)/annots[0](12 0 obj PDPrinterMarkAnnot)

    Detected violation:
    7.18.8-1: A PrinterMark annotation is included in logical structure

    Comment:
    This PDF contains one PrinterMark annotation on page 0. The annotation has
    /Subtype /PrinterMark and is located at page 0 /Annots[0].
    The annotation also has a /StructParent entry. This indicates that the
    annotation is connected to the logical structure tree.

    The element resolved by veraPDF is sufficient to identify the affected annotation element.
    For correction however, we might have to change the /StructParent entry to remove the connection
    to the logical structure tree.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.8-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Annots")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.18.8-1", "root/document[0]/pages[0](7 0 obj PDPage)/annots[0](12 0 obj PDPrinterMarkAnnot)")


def test_resolve_context_verapdf_ua1_example_720t01():
    """
    !Bug in step function gefunden: in line 186: add "xObject" to the name tuple. once
    its added, the test passes.
    veraPDF context:
    root/document[0]/pages[0](23 0 obj PDPage)/contentStream[0](24 0 obj PDSemanticContentStream)/operators[63]/xObject[0]

    Detected violation:
    7.20-1: The document contains a reference XObject (Ref key in the form XObject dictionary)

    Comment:
    in the raw PDF object tree, the affected reference XObject key is under this path:
    page 0 /Resources -> /XObject -> /Fm0 (in the failing PDF, the /Ref key is also nested under the path)

    so the context path given by veraPDF cannot locate the affected element, since it reports it through
    semantic content stream. This is why, the test fails. _resolve_context() probably does not handle this.


    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.20-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Resources").get("/XObject").get("/Fm0")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.20-1", "root/document[0]/pages[0](23 0 obj PDPage)/contentStream[0](24 0 obj PDSemanticContentStream)/operators[63]/xObject[0]")


def test_resolve_context_verapdf_ua1_example_720t02():
    """
    veraPDF context:
    root/document[0]/pages[0](11 0 obj PDPage)/contentStream[0](18 0 obj PDSemanticContentStream)
    /operators[23]/xObject[0]

    Detected violation:
    7.20-2: Form XObject contains MCIDs and is referenced more than once

    Comment:
    MCIDs are present in the stream content of the form XObject, so it is not visible
    as a key in the pdf structure tree. The Form XObject is reached through this path:
    page 0 /Resources -> /XObject -> /Fm0
    Similar to the previous test case (7.20-t01), the context path given by
    veraPDF cannot locate the affected element, since it reports it through semantic content stream.
    Therefore, the test fails.

    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.20-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Resources").get("/XObject").get("/Fm0")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.20-2", "root/document[0]/pages[0](11 0 obj PDPage)/contentStream[0](18 0 obj PDSemanticContentStream)/operators[23]/xObject[0]")

def test_resolve_context_verapdf_ua1_example_72131t01_v2():
    """
    veraPDF context:
    root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](21 0 obj PDSemanticContentStream)
    /operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)


    Detected violation:
    7.21.3.1-1: CIDSystemInfo entries the CIDFont and CMap dictionaries of a Type 0 font are not compatible


    Comment:
    This PDF contains a Type 0 font used from the page content stream. veraPDF
    reports the affected element through the semantic content stream and the text
    operator that uses the font.

    In the raw PDF object tree, the affected font is located in the page resources:

    page 0 /Resources -> /Font -> /C0_0

    The visible difference between the failing and passing PDFs is in the
    descendant CIDFont's /CIDSystemInfo dictionary (which is found under /DescendantFonts). In the failing PDF, the
    /Registry entry is "adobe". In the passing PDF, the /Registry entry is "Adobe". This difference matters because
    the CIDSystemInfo values must be compatible with the CMap used by the Type 0 font.

    As the previous test cases, The veraPDF context path uses the semantic content-stream model, which is not the direct
    pikepdf dictionary path. So the affected element cannot be located through veraPDF context.

    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.3.1-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Resources").get("/Font").get("/C0_0")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.3.1-1", "root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](21 0 obj PDSemanticContentStream)/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)")


def test_resolve_context_verapdf_ua1_example_72132t01_v2():
    """
    veraPDF context:
    root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)
    /operators[9]/font[0](GITMIG+LiberationSans,Bold)/DescendantFonts[0](GITMIG+LiberationSans,Bold)


    Detected violation:
    7.21.3.2-1: A Type 2 CIDFont dictionary has missing or invalid CIDToGIDMap entry


    Important observation:
    The expected affected element exists in the raw PDF object tree at:

    page 0 /Resources -> /Font -> /C2_0 -> /DescendantFonts[0]

    This object is the descendant CIDFont dictionary. It contains the invalid
    /CIDToGIDMap value /NoIdentity. In the passing PDF, the corresponding value is
    /Identity.

    The previous font-related test 7.21.3.1 resolves only the parent Type 0 font and
    passes. This test goes one level deeper into /DescendantFonts[0]. If
    _resolve_context() returns None, the current implementation (in the step function) likely resolves the
    parent font correctly but does not yet support continuing into the
    /DescendantFonts array.

    """
    pytest.skip()
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.3.2-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj.get("/Resources").get("/Font").get("/C2_0").get("/DescendantFonts")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.3.2-1", "root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/operators[9]/font[0](GITMIG+LiberationSans,Bold)/DescendantFonts[0](GITMIG+LiberationSans,Bold)")
        
    
### 
# Test cases files 7.21.3.3-1 to 7.21.8-1, Author: Babett Ludwig
###

#7.21.3.1-t01-fail-c.pdf
#Die technischen Zeichensatzangaben von CIDFont und CMap passen nicht zusammen.
#def test_resolve_context_verapdf_ua1_example_72131t01_v1() :
#    """
#    context path:  root
#    /document[0]
#    /pages[0](12 0 obj PDPage)
#    /contentStream[0](21 0 obj PDSemanticContentStream)
#    /operators[7]
#    /font[0](UMBSME+AdobeGothicStd-Bold)
#    
#    pike pdf path: /Font keys=['/Type', '/ToUnicode', '/BaseFont', '/Encoding', '/Subtype', '/DescendantFonts']
#    
#    The resolved element is sufficient as 'affected element'
#    """
#    pdf_path = generate_resource_path("veraPDF_corpus/7.21.3.1-t01-fail-c.pdf")
#    traverse_pdf_function = lambda pdf: next(iter(pdf.Root.get("/Pages").get("/Kids")[0].get("/Resources").get("/Font").values()))
#    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.3.1-1", "root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](21 0 obj PDSemanticContentStream)/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)") 


#7.21.3.2-t01-fail-c.pdf
#Bei einer CID-Schrift fehlt die Zuordnung von Zeichen-IDs zu Glyphen.
#def test_resolve_context_verapdf_ua1_example_72132t01_v1() :
#    """
#    context path: root
#    /document[0]
#    /pages[0](30 0 obj PDPage)
#    /contentStream[0](31 0 obj PDSemanticContentStream)
#    /operators[9]
#    /font[0](GITMIG+LiberationSans,Bold)
#    /DescendantFonts[0](GITMIG+LiberationSans,Bold)
#    
#    pike pdf path: /Font keys=['/CIDToGIDMap', '/BaseFont', '/CIDSystemInfo', '/Type', '/W', '/Subtype']
#    
#    The resolved element is sufficient as 'affected element'
#    """
#    pdf_path = generate_resource_path("veraPDF_corpus/7.21.3.2-t01-fail-c.pdf")
#    traverse_pdf_function = lambda pdf: list(pdf.Root.get("/Pages").get("/Kids")[0].get("/Resources").get("/Font").values())[0].get("/DescendantFonts")[0]
#    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.3.2-1", "root/document[0]/pages[0](30 0 obj PDPage)/contentStream[0](31 0 obj PDSemanticContentStream)/operators[9]/font[0](GITMIG+LiberationSans,Bold)/DescendantFonts[0](GITMIG+LiberationSans,Bold)") 


#7.21.3.3-t03-fail-a.pdf
#Eine verwendete, nicht standardisierte CMap ist nicht im PDF eingebettet.
def test_resolve_context_verapdf_ua1_example_72133t03() :
    """
    context path: root
    /document[0]
    /pages[0](12 0 obj PDPage)
    /contentStream[0](21 0 obj PDSemanticContentStream)
    /operators[7]
    /font[0](UMBSME+AdobeGothicStd-Bold)
    /Encoding[0](28 0 obj PDCMap)
    /UseCMap[0]
    
    The resolved element is sufficient as 'affected element'
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.3.3-t03-fail-a.pdf")
    traverse_pdf_function = lambda pdf: next(iter(pdf.pages[0].Resources["/Font"].values())).get("/Encoding").get("/UseCMap")
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.3.3-1", "root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](21 0 obj PDSemanticContentStream)/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)/Encoding[0](28 0 obj PDCMap)/UseCMap[0]") 


#7.21.4.1-t01-fail-a.pdf
#Eine zum Anzeigen verwendete Schrift ist nicht im PDF eingebettet.
def test_resolve_context_verapdf_ua1_example_72141t01() :
    """
    context path: root
    /document[0]
    /pages[0](27 0 obj PDPage)
    /contentStream[0](28 0 obj PDSemanticContentStream)
    /operators[4]
    /font[0](Helvetica)
    
    pike pdf path: /Font keys=['/Encoding', '/Type', '/Subtype', '/BaseFont']
    
    The resolved element is sufficient as 'affected element'
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.4.1-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: next(iter(pdf.Root.get("/Pages").get("/Kids")[0].get("/Resources").get("/Font").values()))
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.4.1-1", "root/document[0]/pages[0](27 0 obj PDPage)/contentStream[0](28 0 obj PDSemanticContentStream)/operators[4]/font[0](Helvetica)") 
    
#7.21.4.1-2
#Die eingebettete Schrift enthält nicht alle Zeichenformen, die im Dokument benutzt werden.
    
#7.21.4.2-t01-fail-b.pdf
#Die Glyphenliste einer eingebetteten Type-1-Schrift stimmt nicht mit der Schriftdatei überein.
def test_resolve_context_verapdf_ua1_example_72142t01() :
    """
    context path: root/document[0]/pages[0](17 0 obj PDPage)/contentStream[0](19 0 obj PDSemanticContentStream)/operators[6]/font[0](MIJADQ+AdobeNaskh-Medium)
    
    pike pdf path: /Font keys=['/Type', '/Widths', '/LastChar', '/ToUnicode', '/FirstChar', '/Encoding']
    
    The resolved element is sufficient as 'affected element'
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.4.2-t01-fail-b.pdf")
    traverse_pdf_function = lambda pdf: list(pdf.Root.get("/Pages").get("/Kids")[0].get("/Resources").get("/Font").values())[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.4.2-1", "root/document[0]/pages[0](17 0 obj PDPage)/contentStream[0](19 0 obj PDSemanticContentStream)/operators[6]/font[0](MIJADQ+AdobeNaskh-Medium)") 
    
    
    
#7.21.4.2-t02-fail-a.pdf
# Die CID-Liste einer eingebetteten CID-Schrift beschreibt die enthaltenen Glyphen falsch.
def test_resolve_context_verapdf_ua1_example_72142t02() :
    """
    context path: root
    /document[0]
    /pages[0](17 0 obj PDPage)
    /contentStream[0](18 0 obj PDSemanticContentStream)
    /operators[4]
    /font[0](XIGADL+FreeMonoBold)
    /DescendantFonts[0](XIGADL+FreeMonoBold)
    
    
    pike pdf path: /Font keys=['/CIDToGIDMap', '/FontDescriptor', '/W', '/CIDSystemInfo', '/BaseFont', '/Subtype']
    
    The resolved element is sufficient as 'affected element'
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.4.2-t02-fail-a.pdf")
    traverse_pdf_function = lambda pdf: list(pdf.Root.get("/Pages").get("/Kids")[0].get("/Resources").get("/Font").values())[0].get("/DescendantFonts")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.4.2-2", "root/document[0]/pages[0](17 0 obj PDPage)/contentStream[0](18 0 obj PDSemanticContentStream)/operators[4]/font[0](XIGADL+FreeMonoBold)/DescendantFonts[0](XIGADL+FreeMonoBold)")
     
#7.21.5-t01-fail-a.pdf
#Die Breitenangaben der Schrift stimmen nicht mit den PDF-Breitenangaben überein.
def test_resolve_context_verapdf_ua1_example_7215t01() :
    """
    context path: root/document[0]/pages[0](14 0 obj PDPage)
    /contentStream[0](20 0 obj PDSemanticContentStream)
    /operators[6]
    /usedGlyphs[5](OPCPIB+TimesNewRomanPSMT OPCPIB+TimesNewRomanPSMT 32 0 989889899 0 true)
    
    pike pdf path: /Page keys=['/Rotate', '/MediaBox', '/Resources', '/Contents', '/Tabs', '/StructParents']
    
    is different in passed and failed version: Trailer > /Root > /Pages > /Kids > [0] > /Resources > /Font > /TT0 > /Widths
    
    The resolved element is sufficient as 'affected element'
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.5-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.5-1", "root/document[0]/pages[0](14 0 obj PDPage)/contentStream[0](20 0 obj PDSemanticContentStream)/operators[6]/usedGlyphs[5](OPCPIB+TimesNewRomanPSMT OPCPIB+TimesNewRomanPSMT 32 0 989889899 0 true)")

# 7.21.6-1	
# Eine nichtsymbolische TrueType-Schrift enthält keine passende Unicode-Zeichentabelle.

#7.21.6-t02-fail-d.pdf
#Die Zeichenkodierung einer nichtsymbolischen TrueType-Schrift ist nicht korrekt auf Unicode/Glyphnamen abbildbar.
def test_resolve_context_verapdf_ua1_example_7216t02() :
    """
    context path: root
    /document[0]
    /pages[0](26 0 obj PDPage)
    /contentStream[0](41 0 obj PDSemanticContentStream)
    /operators[5]
    /font[0](BIMHOB+IDAutomationHC39M)
    
    pike pdf path: /Font keys=['/Widths', '/Subtype', '/ToUnicode', '/FontDescriptor', '/Type', '/FirstChar']
    
    The resolved element is sufficient as 'affected element'
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.6-t02-fail-d.pdf")
    traverse_pdf_function = lambda pdf: next(iter(pdf.Root.get("/Pages").get("/Kids")[0].get("/Resources").get("/Font").values()))
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.6-2", "root/document[0]/pages[0](26 0 obj PDPage)/contentStream[0](41 0 obj PDSemanticContentStream)/operators[5]/font[0](BIMHOB+IDAutomationHC39M)") 
    
    
#7.21.6-t03-fail-a.pdf
#Eine symbolische TrueType-Schrift enthält einen Encoding-Eintrag, der dort nicht erlaubt ist.
def test_resolve_context_verapdf_ua1_example_7216t03() :
    """
    context path:  root
    /document[0]
    /pages[0](4 0 obj PDPage)
    /contentStream[0](12 0 obj PDSemanticContentStream)
    /operators[9]
    /font[0](BAAAAA+Verdana)
    
    pike pdf path: /Font keys=['/BaseFont', '/Subtype', '/ToUnicode', '/LastChar', '/FirstChar', '/FontDescriptor']
    
    The resolved element is sufficient as 'affected element'
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.6-t03-fail-a.pdf")
    #you need to use next an iter, because font is a dictionary and not an array
    traverse_pdf_function = lambda pdf: next(iter(pdf.Root.get("/Pages").get("/Kids")[0].get("/Resources").get("/Font").values()))
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.6-3", "root/document[0]/pages[0](4 0 obj PDPage)/contentStream[0](12 0 obj PDSemanticContentStream)/operators[9]/font[0](BAAAAA+Verdana)") 





# 7.21.6-4   Eine symbolische TrueType-Schrift hat keine passende Symbol-Zeichentabelle.
# no pdf file for this rule

#7.21.7-t01-fail-a.pdf
#Ein im Dokument verwendetes Zeichen hat keine Unicode-Zuordnung.
def test_resolve_context_verapdf_ua1_example_7217t01() :
    """
    context path: root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](18 0 obj PDSemanticContentStream)/operators[6]/usedGlyphs[0](JAPTCA+AboriginalSerif JAPTCA+AboriginalSerif 40 0 1141113940 0 true)
    
    
    The “passed” PDF and the “failed” PDF differ significantly from one another
    amongst other things, the following elements are located under “Root” in the “failed” PDF and under “page” in the “passed” PDF:
    /Lang, /PageMode,/MarkInfo, /Metadata, /Outlines, /OutputIntents, /StructureTreeRoot, /ViewerPreferences
    
    In this PDF, there appears to be little correlation between the error message and the actual problem.
    
    The resolved element is not sufficient as 'affected element'
    """
    
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.7-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.7-1", "root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](18 0 obj PDSemanticContentStream)/operators[6]/usedGlyphs[0](JAPTCA+AboriginalSerif JAPTCA+AboriginalSerif 40 0 1141113940 0 true)") 







#7.21.7-t02-fail-c.pdf
#	Eine Unicode-Zuordnung enthält einen verbotenen Unicode-Wert.
def test_resolve_context_verapdf_ua1_example_7217t02() :
    """
    contest path: root/document[0]/pages[0](4 0 obj PDPage)/contentStream[0](13 0 obj PDSemanticContentStream)/operators[9]/usedGlyphs[0](BAAAAA+TimesNewRomanPSMT BAAAAA+TimesNewRomanPSMT 1 0 1233595751 0 true)
    pike pdf path: /Page keys=['/StructParents', '/Tabs', '/Type', '/Parent', '/MediaBox', '/Resources']
    
    In /ToUnicode Trailer > /Root > /Pages > /Kids > [0] > /Resources > /Font > /TT0 > /ToUnicode > /Length, 
    a different number is specified for Length
    a different number is also specified for Trailer > /Size
    and in the passed version there is a Trailer > /Prev
    
    The resolved element is not sufficient as 'affected element'

    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.7-t02-fail-c.pdf")
    traverse_pdf_function = lambda pdf: pdf.pages[0].obj
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.7-2", "root/document[0]/pages[0](4 0 obj PDPage)/contentStream[0](13 0 obj PDSemanticContentStream)/operators[9]/usedGlyphs[0](BAAAAA+TimesNewRomanPSMT BAAAAA+TimesNewRomanPSMT 1 0 1233595751 0 true)") 

#7.21.8-t01-fail-a.pdf 
#	Text verweist auf die .notdef-Glyph, also auf ein nicht definiertes Zeichen.
def test_resolve_context_verapdf_ua1_example_7218t01() :
    """
    context path: root/document[0]/pages[0](21 0 obj PDPage)/contentStream[0](22 0 obj PDSemanticContentStream)/operators[8]/usedGlyphs[0](JNMBGV+KozMinPro-Bold JNMBGV+KozMinPro-Bold 0 0 1620529408 0 true)
    
    The violation is probably located in /Font
    
    The resolved element is partly sufficient as 'affected element'
    
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.8-t01-fail-a.pdf")
    traverse_pdf_function = lambda pdf: pdf.Root.get("/Pages").get("/Kids")[0]
    run_generic_resolve_context_test(pdf_path, traverse_pdf_function, "7.21.8-1", "root/document[0]/pages[0](21 0 obj PDPage)/contentStream[0](22 0 obj PDSemanticContentStream)/operators[8]/usedGlyphs[0](JNMBGV+KozMinPro-Bold JNMBGV+KozMinPro-Bold 0 0 1620529408 0 true)") 

