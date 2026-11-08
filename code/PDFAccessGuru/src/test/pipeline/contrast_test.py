"""Phase 9: colour contrast is always measured; colours change only when the user switches it on."""

from __future__ import annotations

import io

import fitz
import pikepdf
import pytest

from pdfaccessguru.pipeline.contrast import better_color, check_and_fix_contrast, contrast_ratio, find_low_contrast
from pdfaccessguru.pipeline.transaction import WorkingDocument, compare_glyph_positions


def _page(path, gray_text=True) -> bytes:
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 80), "Light grey text is hard to read", fontsize=11, color=(0.67, 0.67, 0.67))
    page.insert_text((72, 110), "Yellow text on white", fontsize=11, color=(1, 0.85, 0.2))
    page.draw_rect(fitz.Rect(60, 130, 400, 160), color=None, fill=(0.05, 0.1, 0.35))
    page.insert_text((72, 150), "White text on dark blue is fine", fontsize=11, color=(1, 1, 1))
    page.insert_text((72, 190), "Black text is fine", fontsize=11, color=(0, 0, 0))
    page.insert_text((72, 230), "Large grey heading", fontsize=20, color=(0.6, 0.6, 0.6))
    gradient = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 256, 20), False)
    for x in range(256):
        for y in range(20):
            gradient.set_pixel(x, y, (x, 255 - x, 128))
    page.insert_image(fitz.Rect(60, 250, 500, 290), pixmap=gradient)
    page.insert_text((72, 275), "Text on a colourful gradient", fontsize=11, color=(1, 1, 1))
    document.save(path)
    return path.read_bytes()


def _colors(path) -> dict[str, int]:
    with fitz.open(path) as document:
        return {span["text"]: span["color"] for block in document[0].get_text("dict")["blocks"]
                for line in block.get("lines", []) for span in line["spans"]}


def test_low_contrast_is_found_with_the_wcag_thresholds(tmp_path):
    low, unclear, hidden = find_low_contrast(_page(tmp_path / "in.pdf"))
    found = {place.text: place for place in low}
    assert set(found) == {"Light grey text is hard to read", "Yellow text on white", "Large grey heading"}
    assert found["Large grey heading"].large and 2.5 < found["Large grey heading"].ratio < 3.0
    assert unclear == 1                                          # the text on the gradient: check by eye


def test_nothing_changes_while_the_option_is_off(tmp_path):
    before = _page(tmp_path / "in.pdf")
    document = WorkingDocument.open(str(tmp_path / "in.pdf"))
    result = check_and_fix_contrast(document, switched_on=False)
    assert result.low_before == 3 and result.fixed == 0 and len(result.low) == 3
    document.save(str(tmp_path / "out.pdf"))
    assert _colors(tmp_path / "out.pdf") == _colors(tmp_path / "in.pdf")
    assert compare_glyph_positions(before, str(tmp_path / "out.pdf")) is None


def test_switched_on_only_the_low_contrast_text_gets_a_new_colour_of_the_same_hue(tmp_path):
    before = _page(tmp_path / "in.pdf")
    document = WorkingDocument.open(str(tmp_path / "in.pdf"))
    result = check_and_fix_contrast(document, switched_on=True)
    document.save(str(tmp_path / "out.pdf"))
    assert result.fixed == 3 and not result.low and not result.undone
    old, new = _colors(tmp_path / "in.pdf"), _colors(tmp_path / "out.pdf")
    for text in ("White text on dark blue is fine", "Black text is fine", "Text on a colourful gradient"):
        assert new[text] == old[text]
    for text in ("Light grey text is hard to read", "Yellow text on white", "Large grey heading"):
        assert new[text] != old[text]
    assert compare_glyph_positions(before, str(tmp_path / "out.pdf")) is None
    assert find_low_contrast((tmp_path / "out.pdf").read_bytes())[0] == []


def test_the_new_colour_keeps_the_hue_and_is_just_enough():
    yellow, white = (255, 217, 51), (255, 255, 255)
    darker = better_color(yellow, white, 4.5)
    assert 4.5 <= contrast_ratio(darker, white) < 5.2
    assert darker[0] > darker[2] and darker[1] > darker[2]          # still a yellow-brown, not grey
    assert better_color((120, 120, 120), (230, 230, 230), 4.5)[0] < 110   # dark text only gets darker
    assert better_color((255, 255, 255), (88, 137, 83), 4.5) is None      # white on mid-green: cannot get lighter


def test_hidden_text_is_never_made_visible_and_light_text_stays_light(tmp_path):
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 80), "Hidden menu text from a saved web page", fontsize=11, color=(0.976, 0.98, 0.98))
    page.draw_rect(fitz.Rect(60, 100, 400, 130), color=None, fill=(0.345, 0.537, 0.325))
    page.insert_text((72, 120), "White on mid green", fontsize=11, color=(1, 1, 1))
    document.save(tmp_path / "in.pdf")
    working = WorkingDocument.open(str(tmp_path / "in.pdf"))
    result = check_and_fix_contrast(working, switched_on=True)
    working.save(str(tmp_path / "out.pdf"))
    assert result.hidden == 1 and result.fixed == 0
    assert [p.text for p in result.low] == ["White on mid green"]        # reported: needs another background
    assert _colors(tmp_path / "out.pdf") == _colors(tmp_path / "in.pdf")


def test_grey_text_stays_grey_and_special_colour_spaces_are_not_touched(tmp_path):
    """The colour system of the text is kept (PDF/A files stay valid); text in other systems is only reported."""
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 80), "placeholder", fontsize=11)
    document.save(tmp_path / "base.pdf")
    with pikepdf.open(tmp_path / "base.pdf") as pdf:
        page = pdf.pages[0]
        font = list(page.Resources.Font.keys())[0]
        page.obj.Resources.ColorSpace = pikepdf.Dictionary(CS0=pikepdf.Array([pikepdf.Name.CalRGB, pikepdf.Dictionary(
            WhitePoint=[0.9505, 1, 1.089])]))
        page.obj.Contents = pdf.make_stream(
            f"BT {font} 11 Tf 0.7 g 72 760 Td (Grey text) Tj ET "
            f"BT {font} 11 Tf /CS0 cs 0.7 0.7 0.7 sc 72 730 Td (Special colour) Tj ET".encode())
        pdf.save(tmp_path / "in.pdf")
    working = WorkingDocument.open(str(tmp_path / "in.pdf"))
    result = check_and_fix_contrast(working, switched_on=True)
    working.save(str(tmp_path / "out.pdf"))
    assert result.low_before == 2 and result.fixed == 1
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        operators = [str(op) for _, op in pikepdf.parse_content_stream(pdf.pages[0])]
    assert "rg" not in operators and "k" not in operators          # the grey text got a darker grey
    assert [t.text for t in result.low] == ["Special colour"]


def test_the_report_says_what_happened_in_plain_words(tmp_path):
    from pdfaccessguru.reporting.customer_report import _contrast_line, _contrast_section

    off = {"switched_on": False, "low_before": 3, "fixed": 0, "unclear": 1, "undone": "", "low_count": 3,
           "pages": [1], "low": [{"page": 1, "text": "Yellow text on white", "ratio": 1.38, "large": False}]}
    text = "\n".join(_contrast_section(off, "en"))
    assert "option “Improve colour contrast” was off" in text and "“Yellow text on white” (page 1, 1.38:1)" in text
    assert "Please look at it yourself" in text and "level AA): 3, on page 1" in text and _contrast_line(off, "en") == ["- Text with too little contrast: 3"]
    on = dict(off, switched_on=True, fixed=3, low_count=0, low=[], pages=[])
    assert "keeping its hue: 3." in "\n".join(_contrast_section(on, "en"))
    assert "Farbton" in "\n".join(_contrast_section(on, "de"))


def test_other_text_on_the_same_line_keeps_its_colour(tmp_path):
    """A black line that overlaps a light grey heading must stay black (found in a real web PDF)."""
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((43, 72), "Answers", fontsize=16, color=(0.784, 0.784, 0.784))
    page.insert_text((45, 68), "meiosis lab answers", fontsize=12, color=(0, 0, 0))
    document.save(tmp_path / "in.pdf")
    working = WorkingDocument.open(str(tmp_path / "in.pdf"))
    result = check_and_fix_contrast(working, switched_on=True)
    working.save(str(tmp_path / "out.pdf"))
    colors = _colors(tmp_path / "out.pdf")
    assert colors["meiosis lab answers"] == 0 and colors["Answers"] != 0xC8C8C8 and result.fixed == 1
