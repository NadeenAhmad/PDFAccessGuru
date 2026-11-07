from pathlib import Path

import pikepdf

from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.registry import detect_affected_element_7_21_3_2_t01
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.registry import detect_affected_element_7_21_7_t02
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.registry import detect_affected_element_7_21_6_t03
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.registry import detect_affected_element_7_21_6_t04
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.registry import detect_affected_element_7_21_6_t01
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.registry import detect_affected_element_7_21_6_t02
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.registry import detect_affected_element_7_21_4_2_t01
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.registry import detect_affected_element_7_21_3_3_t01, detect_affected_element_7_21_3_3_t02, detect_affected_element_7_21_3_3_t03

from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.registry import detect_affected_element_7_21_4_2_t02

from test.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.test_utils import generate_resource_path

########## Example ###########
def test_detect_affected_element_7_21_3_2_t01() :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21.3.2-1",
        clause="7.21.3.2",
        test_number="1",
        description="dummy desc",
        context="root/document[0]/pages[0](30 0 obj PDPage)/contentStream[0](31 0 obj PDSemanticContentStream)/operators[9]/font[0](GITMIG+LiberationSans,Bold)/DescendantFonts[0](GITMIG+LiberationSans,Bold)",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.21.3.2-t01-fail-c.pdf")
    with pikepdf.open(pdf_path) as pdf:
        # warning: this manual traversal does not lead to an element that is needed for correction. 
        # Marwa has to find that element first.
        expected: Object = pdf.pages[0].obj.get("/Resources").get("/Font").get("/C2_0").get("/DescendantFonts")[0]  # type: ignore
        actual = detect_affected_element_7_21_3_2_t01(veraPdf_violation, pdf)

        assert expected == actual
        
        

### 
# Test cases files 7.21.3.3-1 to 7.21.8-1, Author: Babett Ludwig
###

#7.21.3.3-t03-fail-a.pdf
def test_detect_affected_element_7_21_3_3_t03() :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21..3-3",
        clause="7.21.3.3",
        test_number="3",
        description="dummy desc",
        context="root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](21 0 obj PDSemanticContentStream/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)/Encoding[0](28 0 obj PDCMap)/UseCMap[0]",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.21.3.3-t03-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:    
        expected_font = pdf.pages[0].obj.get("/Resources").get("/Font").get("/C0_0")
        actual_font = detect_affected_element_7_21_3_3_t03(veraPdf_violation, pdf)
        assert expected_font == actual_font
        
def test_detect_affected_element_7_21_3_3_t02() :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21.3-3",
        clause="7.21.3.3",
        test_number="2",
        description="dummy desc",
        context="root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](22 0 obj PDSemanticContentStream)/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)/Encoding[0](30 0 obj PDCMap)/embeddedFile[0]",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.21.3.3-t02-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:    
        expected_encoding = pdf.pages[0].obj["/Resources"]["/Font"]["/C0_0"]["/Encoding"]
        actual_encoding = detect_affected_element_7_21_3_3_t02(veraPdf_violation, pdf)
        assert expected_encoding.objgen == actual_encoding.objgen

def test_detect_affected_element_7_21_3_3_t01() :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21..3-3",
        clause="7.21.3.3",
        test_number="1",
        description="dummy desc",
        context="root/document[0]/pages[0](17 0 obj PDPage)/contentStream[0](25 0 obj PDSemanticContentStream)/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.21.3.3-t01-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:    
        expected_font = pdf.pages[0].obj["/Resources"]["/Font"]["/C0_0"]
        actual_font = detect_affected_element_7_21_3_3_t01(veraPdf_violation, pdf)
        assert expected_font.objgen == actual_font.objgen



#detect_affected_element_7_21_4_2_t01
def test_detect_affected_element_7_21_4_2_t01() :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21.4.2-1",
        clause="7.21.4.2",
        test_number="1",
        description="dummy desc",
        context="root/document[0]/pages[0](17 0 obj PDPage)/contentStream[0](19 0 obj PDSemanticContentStream)/operators[6]/font[0](MIJADQ+AdobeNaskh-Medium)",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.21.4.2-t01-fail-b.pdf")
    with pikepdf.open(pdf_path) as pdf:     
        expected_font = pdf.pages[0].obj.get("/Resources").get("/Font").get("/T1_0")
        actual_font = detect_affected_element_7_21_4_2_t01(veraPdf_violation, pdf)
        assert expected_font == actual_font
        
def test_detect_affected_element_7_21_4_2_t02() :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21.4.2-2",
        clause="7.21.4.2",
        test_number="2",
        description="dummy desc",
        context="root/document[0]/pages[0](17 0 obj PDPage)/contentStream[0](18 0 obj PDSemanticContentStream)/operators[4]/font[0](XIGADL+FreeMonoBold)/DescendantFonts[0](XIGADL+FreeMonoBold)",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.21.4.2-t02-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:     
        expected_font_desciptor = pdf.trailer.get("/Root").get("/Pages").get("/Kids")[0].get("/Resources").get("/Font").get("/C2_0").get("/DescendantFonts")[0].get("/FontDescriptor")                  # Zielobjekt
        
        actual_font_descriptor = detect_affected_element_7_21_4_2_t02(veraPdf_violation, pdf)
        print("actual ", actual_font_descriptor)
        print("expected ", expected_font_desciptor)
        assert expected_font_desciptor == actual_font_descriptor        
        
        

def test_detect_affected_element_7_21_6_t01() :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21.6-1",
        clause="7.21.6",
        test_number="1",
        description="dummy desc",
        context="root/document[0]/pages[0](10 0 obj PDPage)/contentStream[0](16 0 obj PDSemanticContentStream)/operators[6]/font[0](BIMHOB+IDAutomationHC39M)/fontFile[0]",
        message="dummy message"
    )

    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.21.6-t01-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:       
        expected_font = pdf.pages[0].obj.get("/Resources").get("/Font").get("/TT0")
        actual_font = detect_affected_element_7_21_6_t01(veraPdf_violation, pdf)
        assert expected_font == actual_font

def test_detect_affected_element_7_21_6_t02() :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21.6-2",
        clause="7.21.6",
        test_number="2",
        description="dummy desc",
        context="root/document[0]/pages[0](26 0 obj PDPage)/contentStream[0](41 0 obj PDSemanticContentStream)/operators[5]/font[0](BIMHOB+IDAutomationHC39M)",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.21.6-t02-fail-d.pdf")
    with pikepdf.open(pdf_path) as pdf:        
        expected_font = pdf.pages[0].obj.get("/Resources").get("/Font").get("/TT0")
        actual_font = detect_affected_element_7_21_6_t02(veraPdf_violation, pdf)
        assert expected_font == actual_font


def test_detect_affected_element_7_21_6_t03() :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21.6-3",
        clause="7.21.6",
        test_number="3",
        description="dummy desc",
        context="root/document[0]/pages[0](4 0 obj PDPage)/contentStream[0](12 0 obj PDSemanticContentStream)/operators[9]/font[0](BAAAAA+Verdana)",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.21.6-t03-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:        
        expected_Font = pdf.pages[0].obj.get("/Resources").get("/Font").get("/TT0")
        actual_Font = detect_affected_element_7_21_6_t03(veraPdf_violation, pdf)
        print("expected Font: ", expected_Font)
        print("acutal Font: ", actual_Font)
        assert expected_Font == actual_Font


def test_detect_affected_element_7_21_6_t04() :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21.6-4",
        clause="7.21.6",
        test_number="4",
        description="dummy desc",
        context="root/document[0]/pages[0](4 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/operators[10]/font[0](BAAAAA+Verdana)/fontFile[0]",
        message="dummy message"
    )

    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.21.6-t04-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:        
        expected_font = pdf.pages[0].obj.get("/Resources").get("/Font").get("/TT0")
        actual_font = detect_affected_element_7_21_6_t04(veraPdf_violation, pdf)
        assert expected_font.objgen == actual_font.objgen




def test_detect_affected_element_7_21_7_t02() :
    veraPdf_violation: VeraPdfViolation = VeraPdfViolation(
        rule_id="7.21.7-2",
        clause="7.21.7",
        test_number="2",
        description="dummy desc",
        context="root/document[0]/pages[0](4 0 obj PDPage)/contentStream[0](13 0 obj PDSemanticContentStream)/operators[9]/usedGlyphs[0](BAAAAA+TimesNewRomanPSMT BAAAAA+TimesNewRomanPSMT 1 0 1233595751 0 true)",
        message="dummy message"
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.21.7-t02-fail-c.pdf")
    with pikepdf.open(pdf_path) as pdf:
        expected_ToUnicode = pdf.pages[0].obj["/Resources"]["/Font"]["/TT0"]["/ToUnicode"]
        actual_ToUnicode= detect_affected_element_7_21_7_t02(veraPdf_violation, pdf)
        print ("expected ToUnicode:", expected_ToUnicode) 
        print ("actual ToUnicode ", actual_ToUnicode)
        assert expected_ToUnicode == actual_ToUnicode

        
