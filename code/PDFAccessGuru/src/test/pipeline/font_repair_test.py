"""
Tests of the font repairs (Phase 3c): embedding missing fonts, matching widths, character tables,
glyph maps, and the mapping of custom tag names.

Embedding needs the Liberation fonts (installed by 'pdfaccessguru doctor --install', as in CI).
System fonts are not used here, so the results are the same on every computer.
"""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

import pikepdf
import pytest
from pikepdf import Array, Dictionary, Name

from pdfaccessguru.external_tools import find_fallback_fonts
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.embed import embed_missing_fonts
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.fonts import (
    all_fonts, find_font_in_context, is_embedded, used_codes,
)
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.sources import normalize, split_style
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.roles import guess_by_name, map_custom_types
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.pipeline.pipeline import run_pipeline
from pdfaccessguru.pipeline.transaction import compare_glyph_positions

RESOURCES = Path(__file__).resolve().parents[1] / "resources"
needs_fonts = pytest.mark.skipif(find_fallback_fonts() is None,
                                 reason="Liberation fonts missing: run 'pdfaccessguru doctor --install'")

# Widths of Helvetica (= Arial = Liberation Sans) for "Hello World" characters.
_HELVETICA = {32: 278, 72: 722, 87: 944, 100: 556, 101: 556, 108: 222, 111: 556, 114: 333}


def _pdf_with_missing_fonts(path: Path, shared_descriptor: bool = False) -> Path:
    """A page with text in two fonts that are not embedded: Helvetica (standard 14, no widths)
    and 'Arial,Bold' (TrueType, WinAnsi, with widths)."""
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    page = pdf.pages[0].obj
    helvetica = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica,
                                             Encoding=Name.WinAnsiEncoding))
    descriptor = pdf.make_indirect(Dictionary(Type=Name.FontDescriptor, FontName=Name("/Arial,Bold"), Flags=32,
                                              FontBBox=[-628, -376, 2000, 1010], ItalicAngle=0, Ascent=905,
                                              Descent=-212, CapHeight=716, StemV=120))
    widths = [_HELVETICA.get(code, 0) for code in range(32, 123)]
    arial_bold = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.TrueType, BaseFont=Name("/Arial,Bold"),
                                              Encoding=Name.WinAnsiEncoding, FirstChar=32, LastChar=122,
                                              Widths=Array(widths), FontDescriptor=descriptor))
    fonts = Dictionary(F1=helvetica, F2=arial_bold)
    content = b"BT /F1 12 Tf 72 700 Td (Hello World) Tj ET BT /F2 12 Tf 72 680 Td (Hello World) Tj ET"
    if shared_descriptor:
        # A second font with the same descriptor but other widths (as Word sometimes writes it).
        other = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.TrueType, BaseFont=Name("/Arial,Bold"),
                                             Encoding=Name.WinAnsiEncoding, FirstChar=32, LastChar=122,
                                             Widths=Array([w + 10 if w else 0 for w in widths]),
                                             FontDescriptor=descriptor))
        fonts["/F3"] = other
        content += b" BT /F3 12 Tf 72 660 Td (Hello World) Tj ET"
    page["/Resources"] = Dictionary(Font=fonts)
    page["/Contents"] = pdf.make_stream(content)
    pdf.save(path)
    return path


@needs_fonts
def test_missing_fonts_are_embedded_and_every_character_stays_in_place(tmp_path):
    source = _pdf_with_missing_fonts(tmp_path / "in.pdf")
    before = source.read_bytes()
    with pikepdf.open(source) as pdf:
        result = embed_missing_fonts(pdf, use_system_fonts=False)
        pdf.save(tmp_path / "out.pdf")
    assert sorted(result.embedded) == ["Arial,Bold", "Helvetica"]
    assert sorted(alike for _, alike in result.look_alikes) == ["LiberationSans-Bold", "LiberationSans-Regular"]
    assert compare_glyph_positions(before, str(tmp_path / "out.pdf")) is None
    rules = {v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf"))}
    assert not {r for r in rules if r.startswith("7.21")}
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        assert all(is_embedded(font) for font in all_fonts(pdf))


@needs_fonts
def test_fonts_sharing_a_descriptor_get_their_own_program(tmp_path):
    source = _pdf_with_missing_fonts(tmp_path / "in.pdf", shared_descriptor=True)
    with pikepdf.open(source) as pdf:
        embed_missing_fonts(pdf, use_system_fonts=False)
        pdf.save(tmp_path / "out.pdf")
        descriptors = {font.FontDescriptor.objgen for font in all_fonts(pdf) if "/FontDescriptor" in font}
        assert len(descriptors) == 3
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.21.4.1-1"] == 0 and rules["7.21.5-1"] == 0


@needs_fonts
def test_a_font_showing_a_character_the_look_alike_lacks_is_left_alone(tmp_path):
    source = _pdf_with_missing_fonts(tmp_path / "in.pdf")
    with pikepdf.open(source, allow_overwriting_input=True) as pdf:
        font = pdf.pages[0].obj.Resources.Font.F2
        font["/Encoding"] = Dictionary(Type=Name.Encoding, BaseEncoding=Name.WinAnsiEncoding,
                                       Differences=Array([72, Name("/uniE000")]))      # private-use glyph
        result = embed_missing_fonts(pdf, use_system_fonts=False)
    assert result.embedded == ["Helvetica"]
    assert result.skipped and result.skipped[0][0] == "Arial,Bold"


@needs_fonts
def test_glyph_position_check_notices_moved_text(tmp_path):
    source = _pdf_with_missing_fonts(tmp_path / "in.pdf")
    before = source.read_bytes()
    with pikepdf.open(source, allow_overwriting_input=True) as pdf:
        pdf.pages[0].obj["/Contents"] = pdf.make_stream(
            b"BT /F1 12 Tf 80 700 Td (Hello World) Tj ET BT /F2 12 Tf 72 680 Td (Hello World) Tj ET")
        pdf.save(tmp_path / "moved.pdf")
    assert "page 1" in compare_glyph_positions(before, str(tmp_path / "moved.pdf"))


def test_used_codes_and_font_lookup_by_context(tmp_path):
    source = _pdf_with_missing_fonts(tmp_path / "in.pdf")
    with pikepdf.open(source) as pdf:
        usage = used_codes(pdf)
        f2 = pdf.pages[0].obj.Resources.Font.F2
        assert usage[f2.objgen] == {ord(c) for c in "Hello World"}
        context = "root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0]/operators[4]/usedGlyphs[0](Arial,Bold Arial,Bold 72 0 1 0 true)"
        assert find_font_in_context(context, pdf).objgen == f2.objgen


@pytest.mark.parametrize("name, expected", [
    ("Arial,BoldItalic", ("arial", "bolditalic")), ("Arial-BoldMT", ("arial", "bold")),
    ("TimesNewRomanPS-ItalicMT", ("timesnewroman", "italic")), ("Times-Roman", ("times", "")),
    ("Helvetica-Oblique", ("helvetica", "italic")), ("CourierNewPSMT", ("couriernew", "")),
])
def test_font_names_are_read_like_a_person_would(name, expected):
    assert split_style(name) == expected


def test_font_flags_add_the_style_the_name_leaves_out():
    assert split_style("Arial", font_flags=1 << 18) == ("arial", "bold")
    assert normalize("Times New Roman,Bold") == normalize("TimesNewRomanPS-BoldMT")


# --- the whole pipeline on veraPDF's test files ---------------------------------------------------

@needs_fonts
@pytest.mark.parametrize("name, rule", [
    ("veraPDF_corpus/7.21.4.1-t01-fail-a.pdf", "7.21.4.1-1"),
    ("veraPDF_corpus/7.21.5-t01-fail-a.pdf", "7.21.5-1"),
    ("PDFAccessGuru_corpus/7.21.6-t01-fail-a.pdf", "7.21.6-1"),
    ("PDFAccessGuru_corpus/7.21.6-t04-fail-a.pdf", "7.21.6-4"),
    ("veraPDF_corpus/7.21.3.2-t01-fail-a.pdf", "7.21.3.2-1"),
    ("veraPDF_corpus/7.21.3.2-t01-fail-b.pdf", "7.21.3.2-1"),
    ("veraPDF_corpus/7.21.3.2-t01-fail-c.pdf", "7.21.3.2-1"),
    ("veraPDF_corpus/7.1-t02-fail-a.pdf", "7.1-2"),
    ("veraPDF_corpus/7.1-t04-fail-a.pdf", "7.1-4"),
    ("veraPDF_corpus/7.1-t05-fail-a.pdf", "7.1-5"),
    ("veraPDF_corpus/7.1-t05-fail-b.pdf", "7.1-5"),
    ("veraPDF_corpus/7.1-t05-fail-c.pdf", "7.1-5"),
    ("veraPDF_corpus/7.1-t05-fail-d.pdf", "7.1-6"),
    ("veraPDF_corpus/7.1-t06-fail-a.pdf", "7.1-6"),
])
def test_pipeline_fixes_the_problem_without_new_ones(tmp_path, name, rule):
    source = tmp_path / Path(name).name
    shutil.copy(RESOURCES / name, source)
    before = Counter(v.rule_id for v in run_verapdf(str(source)))
    assert before[rule] > 0
    run_pipeline(str(source), str(tmp_path / "out.pdf"))
    after = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert after[rule] == 0
    assert sum(after.values()) < sum(before.values())


# --- custom tag names ------------------------------------------------------------------------------

@pytest.mark.parametrize("name, tag", [
    ("Footnote", "Note"), ("GoTo", "Link"), ("URI", "Link"), ("Lbody", "LBody"), ("Überschrift 2", "H2"),
    ("Heading 3", "H3"), ("Standard", "P"), ("Normal", "P"), ("TextBox", "Div"), ("InlineShape", "Figure"),
    ("Chart", "Figure"), ("Contents 2", "TOCI"), ("Underline", "Span"), ("Fade", None), ("SIS", None),
])
def test_custom_tag_names_are_mapped_by_what_they_say(name, tag):
    assert guess_by_name(name) == tag


def test_names_that_say_nothing_are_mapped_by_their_content_and_listed_for_checking():
    pdf = pikepdf.new()
    root = pdf.make_indirect(Dictionary(Type=Name.StructTreeRoot))
    document = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.Document, P=root))
    group = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name("/Fade"), P=document))
    text = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name("/SIS"), P=group, K=0))
    footnote = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name("/Footnote"), P=document, K=1))
    group["/K"] = Array([text])
    document["/K"] = Array([group, footnote])
    root["/K"] = Array([document])
    root["/RoleMap"] = Dictionary({"/LI": Name("/LI")})                    # a standard tag in a circle
    pdf.Root["/StructTreeRoot"] = root

    result = map_custom_types(pdf)

    assert result.mapped == {"Fade": "Div", "SIS": "P", "Footnote": "Note"}
    assert sorted(result.guessed) == ["Fade", "SIS"]
    assert result.removed == ["LI"]
    assert "/LI" not in root.RoleMap and root.RoleMap["/Footnote"] == Name("/Note")


def test_font_names_that_are_not_utf8_do_not_stop_the_font_repairs():
    """A Japanese font name in Shift-JIS (found in a real file): reading it failed, so the missing
    CIDToGIDMap was never written. veraPDF prints the name with replacement characters."""
    import pikepdf

    from pdfaccessguru.utils.pdf_names import name_text, same_font_name

    name = pikepdf.Object.parse(b"/PPSKOA+ARP#83S#83V#83b#83N")
    text = name_text(name)
    assert text.startswith("/PPSKOA+ARP") and len(text) == len("/PPSKOA+ARP") + 8
    assert same_font_name(text.lstrip("/"), "PPSKOA+ARP�ۃS�V�b�N")
    assert not same_font_name("OTHERF+Arial", "PPSKOA+ARP�S")
    assert same_font_name("Arial", "Arial") and not same_font_name("Arial", "Arial-Bold")
