import pytest


from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    run_generic_corrector_test,
    
)
from .run_generic_supplementary_information import (
    run_generic_supplementary_information_corrector_test,
)
from .run_generic_corrector_debug_test import (
    run_generic_corrector_debug_test,
)
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_document_reference_notdef_glyph,
)



def test_a_missing_glyph_in_a_composite_font_is_left_alone():
    """veraPDF's sample: a CID in a Japanese composite font maps to .notdef. Editing the text cannot
    repair a missing glyph, and deleting the character would change the text, so it is refused
    and nothing changes (Phase 11; the first version deleted the character)."""
    import pikepdf

    from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
        CouldNotCorrectDetectedViolationException,
    )
    from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import generate_resource_path

    with pikepdf.open(generate_resource_path("veraPDF_corpus/7.21.8-t01-fail-a.pdf")) as pdf:
        before = pdf.pages[0].Contents.read_bytes()
        with pytest.raises(CouldNotCorrectDetectedViolationException):
            correct_document_reference_notdef_glyph(None, pdf)
        assert pdf.pages[0].Contents.read_bytes() == before


def test_tabs_without_a_glyph_are_removed_and_the_letters_stay_in_place(tmp_path):
    """The real cases: tabs and line breaks in the text of simple fonts. They are removed; a width
    the font gives them is kept as a text shift, so no letter moves."""
    from collections import Counter

    import pymupdf as fitz
    import pikepdf

    from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf

    document = fitz.open()
    document.new_page(width=595, height=842).insert_text((72, 80), "placeholder", fontsize=11)
    document.save(tmp_path / "base.pdf")
    with pikepdf.open(tmp_path / "base.pdf") as pdf:
        page = pdf.pages[0]
        widths = [0] * 9 + [500] + [0] * 22 + [278] + [600] * 95           # codes 0..127; the tab is 500 wide
        page.obj.Resources.Font = pikepdf.Dictionary(F9=pikepdf.Dictionary(
            Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type1, BaseFont=pikepdf.Name.Helvetica,
            Encoding=pikepdf.Name.WinAnsiEncoding, FirstChar=0, LastChar=127, Widths=widths))
        page.obj.Contents = pdf.make_stream(b"BT /F9 11 Tf 72 760 Td (Name\tValue) Tj ET "
                                            b"BT /F9 11 Tf 72 730 Td (Total) Tj (\t) Tj (42) Tj ET")
        pdf.save(tmp_path / "in.pdf")
    def letters(path):
        with fitz.open(path) as d:
            return [(c["c"], round(c["origin"][0], 2), round(c["origin"][1], 2))
                    for b in d[0].get_text("rawdict")["blocks"] for l in b.get("lines", [])
                    for sp in l["spans"] for c in sp["chars"] if c["c"].strip() and ord(c["c"]) >= 32]
    with pikepdf.open(tmp_path / "in.pdf") as pdf:
        correct_document_reference_notdef_glyph(None, pdf)
        pdf.save(tmp_path / "out.pdf")
        shown = b"".join(bytes(s) for o, op in pikepdf.parse_content_stream(pdf.pages[0]) if str(op) in ("Tj", "TJ")
                         for s in (o[0] if str(op) == "TJ" else [o[0]]) if isinstance(s, pikepdf.String))
    assert b"\t" not in shown and b"Name" in shown and b"Value" in shown
    assert letters(tmp_path / "out.pdf") == letters(tmp_path / "in.pdf")
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.21.8-1"] == 0


def test_correct_document_reference_notdef_glyph_ProfPDFs():
    """
    Tests correction of .notdef glyph references (7.21.8-1).
    """

    def affected_element_detector(pdf):
     
        return pdf.pages[125]

    def supplementary_information_extractor(pdf):
        page = pdf.pages[125].obj
        font = pdf.pages[125].obj["/Resources"]["/Font"]["/F1"] 

        to_unicode = font.get("/ToUnicode")            # ToUnicode Map
        operator_index = 1140
        glyph_index = 9 
        
        return [page, to_unicode, operator_index, glyph_index]

    run_generic_supplementary_information_corrector_test(
        rule_id="7.21.8-1",
        test_pdf_file="ProfPDFs/10589-ENRICH.pdf",
        corrector=correct_document_reference_notdef_glyph,
        context=(
            "root/document[0]/pages[125](1095 0 obj PDPage)"
            "/contentStream[0](1119 0 obj PDSemanticContentStream)/operators[1140]"
            "/usedGlyphs[9](ABCXYZ+Calibri-Italic ABCXYZ+Calibri-Italic 0 0 2055967078 338 true)"
        ),
        affected_element_detector=affected_element_detector,
        supplementary_information_extractor=supplementary_information_extractor,
    )
