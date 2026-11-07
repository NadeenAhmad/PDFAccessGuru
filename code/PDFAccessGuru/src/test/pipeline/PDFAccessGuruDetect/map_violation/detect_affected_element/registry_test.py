import pytest
import pikepdf
from pikepdf import Object

from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.registry import (
    detect_affected_element_7_2_30,
    detect_affected_element_7_2_31,
    detect_affected_element_7_2_32,
    detect_affected_element_7_2_33,
    detect_affected_element_7_2_34,
    detect_affected_element_7_21_3_2_t01,
    detect_affected_element_7_2_t17, 
    detect_affected_element_7_2_t18,
    detect_affected_element_7_20_t01,
    detect_affected_element_7_20_t02,
    detect_affected_element_7_21_3_1_t01,
    detect_affected_element_7_21_3_2_t01,
    detect_affected_element_7_21_3_2_t01,
    detect_affected_element_7_1_8,
    detect_affected_element_7_1_9,
    detect_affected_element_7_1_10,
    detect_affected_element_7_1_11,
    detect_affected_element_7_2_2,
)
from test.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.test_utils import generate_resource_path



### 
# Tests for affected element detectors, rule_ids 7.1-7 to 7.2-8, Author: Siju Li
###

def test_detect_affected_element_7_1_8():
    """
    Rule 7.1-8 (metadata-key-missing). VeraPDF context "root/document[0]"
    resolves to the whole Pdf object via the default step function, which
    would raise ResolveContextReturnsWholePdfException. The custom detector
    bypasses this and returns pdf.Root directly.
    """
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.1-8",
        clause="7.1",
        test_number="8",
        description="dummy desc",
        context="root/document[0]",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t08-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        expected: Object = pdf.Root
        actual = detect_affected_element_7_1_8(veraPdf_violation, pdf)

        assert expected == actual


def test_detect_affected_element_7_1_9():
    """
    Rule 7.1-9 (missing-metadata-stream-dc-title). VeraPDF context
    "root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]" would
    raise a StepFunctionTraversalException via the default step function,
    since RESOLVERS only registers "Metadata" (capitalized), not "metadata".
    The custom detector bypasses resolve_context and accesses the metadata
    stream directly via pdf.Root.get("/Metadata").
    """
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.1-9",
        clause="7.1",
        test_number="9",
        description="dummy desc",
        context="root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t09-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        expected: Object = pdf.Root.get("/Metadata") #type: ignore
        actual = detect_affected_element_7_1_9(veraPdf_violation, pdf)

        assert expected == actual


def test_detect_affected_element_7_1_10():
    """
    Rule 7.1-10 (display-doc-title-false). VeraPDF context "root" resolves
    to the whole Pdf object via handle_root, which would raise
    ResolveContextReturnsWholePdfException. The custom detector returns
    pdf.Root directly.
    """
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.1-10",
        clause="7.1",
        test_number="10",
        description="dummy desc",
        context="root",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t10-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        expected: Object = pdf.Root
        actual = detect_affected_element_7_1_10(veraPdf_violation, pdf)

        assert expected == actual


def test_detect_affected_element_7_1_11():
    """
    Rule 7.1-11 (missing-struct-tree-root-entry). VeraPDF context
    "root/document[0]" resolves to the whole Pdf object, same situation as
    7.1-8. The custom detector returns pdf.Root directly.
    """
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.1-11",
        clause="7.1",
        test_number="11",
        description="dummy desc",
        context="root/document[0]",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t11-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        expected: Object = pdf.Root
        actual = detect_affected_element_7_1_11(veraPdf_violation, pdf)

        assert expected == actual


def test_detect_affected_element_7_2_2():
    """
    Rule 7.2-2 (natural-language-undefined). VeraPDF context
    "root/document[0]/Outlines[0](outline 13 0)" would resolve via
    handle_Outlines, which ignores the index and always returns the whole
    /Outlines dictionary - not what the corrector needs. The custom detector
    returns pdf.Root directly, since correct_natural_language_undefined sets
    /Lang on the document catalog.
    """
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.2-2",
        clause="7.2",
        test_number="2",
        description="dummy desc",
        context="root/document[0]/Outlines[0](outline 13 0)",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t02-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        expected: Object = pdf.Root
        actual = detect_affected_element_7_2_2(veraPdf_violation, pdf)

        assert expected == actual

# command: python -m pytest -v test/pipeline/PDFAccessGuruDetect/map_violation/detect_affected_element/registry_test.py
# End Siju Li


### 
# Test cases for affected element detectors for rule_ids 7.5-7 to 7.18.1-3, Author: Robin Hart
###


def test_detect_affected_element_7_2_t17() :
    """
    To test: is parent element of resolved element returned?
    """
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.2-17",
        clause="7.2",
        test_number="17",
        description="dummy desc",
        context="root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[1](27 0 obj SELI LI)",
        message="dummy message"
    )
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t17-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        expected: Object = pdf.Root.get("/StructTreeRoot").get("/K") #type: ignore
        actual = detect_affected_element_7_2_t17(veraPdf_violation, pdf)
        assert expected == actual

def test_detect_affected_element_7_2_t18() :
    """
    To test: is parent element of resolved element returned?
    """
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.2-18",
        clause="7.2",
        test_number="18",
        description="dummy desc",
        context="root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)/K[0](15 0 obj SEDocument Document)/K[1](27 0 obj SELBody LBody)",
        message="dummy message"
    )
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t18-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        expected: Object = pdf.Root.get("/StructTreeRoot").get("/K") #type: ignore
        actual = detect_affected_element_7_2_t18(veraPdf_violation, pdf)
        assert expected == actual

# End test case Robin Hart


### 
# Test cases for affected element detectors for rule_ids 7.5-7 to 7.18.1-3, Author: Riard Qupevaj
###


def _run_mcid_detector_test(rule_id: str, pdf_file: str, context: str, detector):
    veraPdf_violation = VeraPdfViolation(
        rule_id=rule_id,
        clause=rule_id.rsplit("-", 1)[0],
        test_number=rule_id.rsplit("-", 1)[1],
        description="dummy desc",
        context=context,
        message="dummy message",
    )

    pdf_path = generate_resource_path(f"veraPDF_corpus/{pdf_file}")
    with pikepdf.open(pdf_path) as pdf:
        expected = pdf.Root.get("/StructTreeRoot").get("/ParentTree").get("/Nums")[1][0]
        actual = detector(veraPdf_violation, pdf)
        assert expected == actual
        assert actual != pdf.pages[0].obj


def test_detect_affected_element_7_2_30_uses_parent_tree_mcid():
    _run_mcid_detector_test(
        "7.2-30",
        "7.2-t30-fail-a.pdf",
        "root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/content[1]{mcid:0}/contentItem[0]{mcid:0}",
        detect_affected_element_7_2_30,
    )


def test_detect_affected_element_7_2_31_uses_parent_tree_mcid():
    _run_mcid_detector_test(
        "7.2-31",
        "7.2-t31-fail-a.pdf",
        "root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/content[1]{mcid:0}/contentItem[0]{mcid:0}",
        detect_affected_element_7_2_31,
    )


def test_detect_affected_element_7_2_32_uses_parent_tree_mcid():
    _run_mcid_detector_test(
        "7.2-32",
        "7.2-t32-fail-a.pdf",
        "root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/content[1]{mcid:0}/contentItem[0]{mcid:0}",
        detect_affected_element_7_2_32,
    )


def test_detect_affected_element_7_2_34_uses_parent_tree_mcid():
    _run_mcid_detector_test(
        "7.2-34",
        "7.2-t34-fail-a.pdf",
        "root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/content[1]{mcid:0}/contentItem[0]{mcid:0}",
        detect_affected_element_7_2_34,
    )


def test_detect_affected_element_7_2_33_uses_indirect_metadata_object():
    veraPdf_violation = VeraPdfViolation(
        rule_id="7.2-33",
        clause="7.2",
        test_number="33",
        description="dummy desc",
        context="root/indirectObjects[265](48 0)/directObject[0]/metadata[0](49 0 obj PDMetadata)/XMPPackage[0]/Properties[13](http://purl.org/dc/elements/1.1/ - dc:title)",
        message="dummy message",
    )

    pdf_path = generate_resource_path("ProfPDFs/asi-05-00089.pdf")
    with pikepdf.open(pdf_path) as pdf:
        expected = pdf.get_object((49, 0))
        actual = detect_affected_element_7_2_33(veraPdf_violation, pdf)
        assert expected == actual
        
# End test case Riard  



### 
# Test cases for affected element detectors for rule_ids 7.5-7 to 7.18.1-3, Author: Marwa Ayache
###

def test_detect_affected_element_7_20_t01() :
    veraPdf_violation = VeraPdfViolation(
        rule_id="7.20-1",
        clause="7.20",
        test_number="1",
        description="dummy desc",
        context="root/document[0]/pages[0](23 0 obj PDPage)/contentStream[0](24 0 obj PDSemanticContentStream)/operators[63]/xObject[0]",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.20-t01-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        expected = pdf.pages[0].obj.get("/Resources").get("/XObject").get("/Fm0")  # type: ignore[union-attr]
        actual = detect_affected_element_7_20_t01(veraPdf_violation, pdf)

        assert expected == actual


def test_detect_affected_element_7_20_t02() :
    veraPdf_violation = VeraPdfViolation(
        rule_id="7.20-2",
        clause="7.20",
        test_number="2",
        description="dummy desc",
        context="root/document[0]/pages[0](11 0 obj PDPage)/contentStream[0](18 0 obj PDSemanticContentStream)/operators[23]/xObject[0]",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.20-t02-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        expected = pdf.pages[0].obj.get("/Resources").get("/XObject").get("/Fm0")  # type: ignore[union-attr]
        actual = detect_affected_element_7_20_t02(veraPdf_violation, pdf)

        assert expected == actual


@pytest.mark.parametrize("pdf_name", [
    "veraPDF_corpus/7.21.3.1-t01-fail-a.pdf",
    "veraPDF_corpus/7.21.3.1-t01-fail-b.pdf",
    "veraPDF_corpus/7.21.3.1-t01-fail-c.pdf",
])
def test_detect_affected_element_7_21_3_1_t01(pdf_name: str) :
    veraPdf_violation = VeraPdfViolation(
        rule_id="7.21.3.1-1",
        clause="7.21.3.1",
        test_number="1",
        description="dummy desc",
        context="root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](21 0 obj PDSemanticContentStream)/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)",
        message="dummy message"
    )

    pdf_path = generate_resource_path(pdf_name)
    with pikepdf.open(pdf_path) as pdf:
        expected = pdf.pages[0].obj.get("/Resources").get("/Font").get("/C0_0")  # type: ignore[union-attr]
        actual = detect_affected_element_7_21_3_1_t01(veraPdf_violation, pdf)

        assert expected == actual


@pytest.mark.parametrize("pdf_name", [
    "veraPDF_corpus/7.21.3.2-t01-fail-a.pdf",
    "veraPDF_corpus/7.21.3.2-t01-fail-b.pdf",
    "veraPDF_corpus/7.21.3.2-t01-fail-c.pdf",
])
def test_detect_affected_element_7_21_3_2_t01(pdf_name: str) :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21.3.2-1",
        clause="7.21.3.2",
        test_number="1",
        description="dummy desc",
        context="root/document[0]/pages[0](30 0 obj PDPage)/contentStream[0](31 0 obj PDSemanticContentStream)/operators[9]/font[0](GITMIG+LiberationSans,Bold)/DescendantFonts[0](GITMIG+LiberationSans,Bold)",
        message="dummy message"
    )

    pdf_path = generate_resource_path(pdf_name)
    with pikepdf.open(pdf_path) as pdf:
        expected: Object = pdf.pages[0].obj.get("/Resources").get("/Font").get("/C2_0").get("/DescendantFonts")[0]  # type: ignore
        actual = detect_affected_element_7_21_3_2_t01(veraPdf_violation, pdf)

        assert expected == actual

# End test case Marwa Ayache  

