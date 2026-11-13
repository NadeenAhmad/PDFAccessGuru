"""1.1: figures drawn with vector drawings or cut into raster pieces, and display formulas, in the automatic tagger."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pikepdf
import pymupdf as fitz
import pytest

from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.pipeline.transaction import compare_glyph_positions, compare_pages
from pdfaccessguru.tagging.builder import tag_document
from pdfaccessguru.tagging.formulas import formula_spoken_text

_TEXT = "The survey shows clearly that the method works well for most of the documents we tested."


def _kids(element) -> list:
    kids = element.get("/K")
    return list(kids) if isinstance(kids, pikepdf.Array) else [kids] if kids is not None else []


def _elements(pdf: pikepdf.Pdf, tag: str) -> list:
    return [kid for kid in _kids(pdf.Root.StructTreeRoot.K[0]) if isinstance(kid, pikepdf.Dictionary)
            and kid.get("/S") == pikepdf.Name("/" + tag)]


def _marks(pdf: pikepdf.Pdf, page_index: int = 0) -> Counter:
    """(operator kind, tag of the marked content around it) for every painted path, picture and text."""
    found: Counter = Counter()
    stack: list[str] = []
    for operands, operator in pikepdf.parse_content_stream(pdf.pages[page_index]):
        name = str(operator)
        if name in ("BMC", "BDC"):
            stack.append(str(operands[0]))
        elif name == "EMC" and stack:
            stack.pop()
        elif name in ("f", "F", "f*", "S", "s", "B", "b"):
            found[("path", stack[-1] if stack else None)] += 1
        elif name in ("Do", "INLINE IMAGE"):
            found[("picture", stack[-1] if stack else None)] += 1
        elif name in ("Tj", "TJ"):
            found[("text", stack[-1] if stack else None)] += 1
    return found


def _tag(source: Path, target: Path):
    with pikepdf.open(source) as pdf:
        result = tag_document(pdf)
        pdf.save(target)
    return result


def _page_with_text(document: fitz.Document) -> fitz.Page:
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 80), "1 Results", fontsize=16, fontname="hebo")
    page.draw_line((72, 90), (523, 90), width=0.5)                   # a rule under the heading
    page.insert_text((72, 120), _TEXT, fontsize=10)
    page.insert_text((72, 134), "It was tested on many files from different sources and programs.", fontsize=10)
    return page


def _bar_chart_pdf(path: Path) -> Path:
    """A heading with a rule, a paragraph, a bar chart drawn with lines and shapes, its caption."""
    document = fitz.open()
    page = _page_with_text(document)
    left, bottom = 120, 400
    page.draw_line((left, bottom), (left + 260, bottom), width=1)       # x axis
    page.draw_line((left, bottom), (left, bottom - 200), width=1)       # y axis
    for number, height in enumerate((120, 180, 60, 150)):
        x = left + 20 + number * 60
        page.draw_rect(fitz.Rect(x, bottom - height, x + 40, bottom), color=None, fill=(0.2, 0.4, 0.8))
        page.insert_text((x + 16, bottom + 12), "ABCD"[number], fontsize=8)
    for tick, value in enumerate(("0", "50", "100")):
        y = bottom - tick * 90
        page.draw_line((left - 4, y), (left, y), width=0.5)
        page.insert_text((left - 20, y + 3), value, fontsize=8)
    page.insert_text((left + 100, bottom + 26), "Group", fontsize=8)
    page.insert_text((72, 450), "Figure 1: Number of answers per group", fontsize=9)
    page.insert_text((72, 480), _TEXT, fontsize=10)
    document.save(path)
    return path


def test_a_vector_bar_chart_is_one_figure_with_its_labels_and_a_bounding_box(tmp_path):
    source = _bar_chart_pdf(tmp_path / "chart.pdf")
    before = source.read_bytes()
    result = _tag(source, tmp_path / "out.pdf")
    assert result.elements["Figure"] == 1 and result.elements["Caption"] == 1
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        figure = _elements(pdf, "Figure")[0]
        assert str(figure.A.O) == "/Layout"
        x0, y0, x1, y1 = (float(value) for value in figure.A.BBox)
        # the bars, axes, ticks and labels (PDF coordinates: y grows upwards)
        assert 95 < x0 < 120 and 375 < x1 < 385 and 842 - 430 < y0 < 842 - 400 and 842 - 205 < y1 < 842 - 195
        marks = _marks(pdf)
        assert marks[("path", "/Figure")] >= 4 + 2 + 3                # bars, axes, ticks
        assert marks[("path", "/Artifact")] == 1                       # the rule under the heading
        assert marks[("text", "/Figure")] >= 4 + 3 + 1                 # bar names, tick values, axis title
        texts = [str(element.S) for element in _kids(pdf.Root.StructTreeRoot.K[0])]
        assert texts.count("/P") == 2                                  # the paragraphs stay text
    assert compare_glyph_positions(before, str(tmp_path / "out.pdf")) is None
    assert compare_pages(before, str(tmp_path / "out.pdf"), compare_all=True, check_text=True,
                         strong_tolerance=0.001) is None
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.1-3"] == 0 and rules["7.3-1"] == 1               # the description comes from the 7.3-1 fix


def test_table_rules_frames_and_text_boxes_stay_decoration(tmp_path):
    """A ruled table, a table with only horizontal rules, and a framed text box: no figures."""
    document = fitz.open()
    page = _page_with_text(document)
    rows = [["Measure", "Group A", "Group B"], ["Time (min)", "1:41", "2:05"], ["Errors", "3", "5"]]
    left, top, width, height = 72, 160, 150, 24
    for r in range(len(rows) + 1):
        page.draw_line((left, top + r * height), (left + 3 * width, top + r * height))
    for c in range(4):
        page.draw_line((left + c * width, top), (left + c * width, top + len(rows) * height))
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            page.insert_text((left + c * width + 6, top + r * height + 16), text, fontsize=10)
    top = 300                                                          # rules only (booktabs)
    for y in (top, top + 20, top + 70):
        page.draw_line((left, y), (left + 300, y), width=0.8)
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            page.insert_text((left + 6 + c * 100, top + 15 + r * 20), text, fontsize=10)
    box = fitz.Rect(72, 420, 523, 480)                                 # a shaded box around a paragraph
    page.draw_rect(box, color=(0, 0, 0), fill=(0.9, 0.9, 0.9))
    page.insert_text((80, 440), _TEXT, fontsize=10)
    page.insert_text((80, 455), "Note: all times are rounded to the minute.", fontsize=10)
    document.save(tmp_path / "in.pdf")
    result = _tag(tmp_path / "in.pdf", tmp_path / "out.pdf")
    assert result.elements["Figure"] == 0 and result.elements["Table"] == 1
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        marks = _marks(pdf)
        assert marks[("path", "/Figure")] == 0 and marks[("text", "/Figure")] == 0


def test_touching_picture_pieces_are_one_figure_and_tiny_dots_are_decoration(tmp_path):
    document = fitz.open()
    page = _page_with_text(document)
    piece = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), False)
    for number, shade in enumerate((60, 120, 180)):                    # one picture in three touching pieces
        piece.clear_with(shade)
        page.insert_image(fitz.Rect(100 + number * 80, 200, 180 + number * 80, 300), pixmap=piece)
    piece.clear_with(30)
    page.insert_image(fitz.Rect(400, 150, 410, 160), pixmap=piece)     # a tiny picture
    page.draw_circle((450, 155), 3, color=None, fill=(0, 0, 0))        # a dot
    page.insert_text((72, 330), "Figure 2: A picture in three parts", fontsize=9)
    document.save(tmp_path / "in.pdf")
    result = _tag(tmp_path / "in.pdf", tmp_path / "out.pdf")
    assert result.elements["Figure"] == 1
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        figure = _elements(pdf, "Figure")[0]
        x0, y0, x1, y1 = (float(value) for value in figure.A.BBox)
        assert abs(x0 - 100) < 2 and abs(x1 - 340) < 2 and abs(y0 - 542) < 2 and abs(y1 - 642) < 2
        marks = _marks(pdf)
        assert marks[("picture", "/Figure")] == 3 and marks[("picture", "/Artifact")] == 1
        assert marks[("path", "/Figure")] == 0


def test_a_chart_with_grid_lines_is_a_figure_not_a_table(tmp_path):
    """The table finder sees a grid; a data line across it and empty cells show it is a chart."""
    document = fitz.open()
    page = _page_with_text(document)
    left, top, size = 150, 180, 200
    for step in range(5):
        page.draw_line((left + step * 50, top), (left + step * 50, top + size), width=0.4)
        page.draw_line((left, top + step * 50), (left + size, top + step * 50), width=0.4)
        page.insert_text((left + step * 50 - 3, top + size + 12), str(step * 10), fontsize=8)
    page.draw_polyline([(left, top + 190), (left + 60, top + 120), (left + 130, top + 90), (left + 200, top + 10)],
                       color=(0.8, 0.1, 0.1), width=1.5)
    page.insert_text((left + 8, top + 20), "Sales", fontsize=8)        # a legend inside the plot
    page.insert_text((72, 430), "Figure 3: Growth over ten years", fontsize=9)
    document.save(tmp_path / "in.pdf")
    with fitz.open(tmp_path / "in.pdf") as check:
        assert check[0].find_tables().tables                          # the grid looks like a table
    result = _tag(tmp_path / "in.pdf", tmp_path / "out.pdf")
    assert result.elements["Table"] == 0 and result.elements["Figure"] == 1
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        marks = _marks(pdf)
        assert marks[("path", "/Figure")] >= 11 and marks[("text", "/Figure")] == 6


def test_pictures_in_a_grid_are_one_figure_two_side_by_side_stay_two(tmp_path):
    document = fitz.open()
    page = _page_with_text(document)
    piece = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 20, 20), False)
    for row in range(2):                                               # 3 x 2 panels with 15 pt gaps
        for col in range(3):
            piece.clear_with(40 + 30 * (row * 3 + col))
            x, y = 90 + col * 135, 170 + row * 135
            page.insert_image(fitz.Rect(x, y, x + 120, y + 120), pixmap=piece)
    page.insert_text((72, 450), "Figure 4: Six samples", fontsize=9)
    for col in range(2):                                               # two figures, one in each column
        piece.clear_with(90 + 60 * col)
        page.insert_image(fitz.Rect(72 + col * 240, 480, 282 + col * 240, 640), pixmap=piece)
        page.insert_text((72 + col * 240, 655), f"Figure {5 + col}: A sample", fontsize=9)
    document.save(tmp_path / "in.pdf")
    result = _tag(tmp_path / "in.pdf", tmp_path / "out.pdf")
    assert result.elements["Figure"] == 3


def _cjk_font(page: fitz.Page) -> str:
    """A font with Greek letters and math signs (built into PyMuPDF)."""
    page.insert_font(fontname="F9", fontbuffer=fitz.Font("cjk").buffer)
    return "F9"


def _formula_pdf(path: Path) -> Path:
    document = fitz.open()
    page = _page_with_text(document)
    font = _cjk_font(page)
    page.insert_text((72, 170), "The model is fitted with gradient descent on the training data.", fontsize=10)
    page.insert_text((200, 200), "y = α + β · x²", fontsize=11, fontname=font)
    page.insert_text((500, 200), "(1)", fontsize=10)
    page.insert_text((72, 230), "where α is the offset, β the slope and x ≥ 0 the input value.", fontsize=10,
                     fontname=font)
    page.insert_text((72, 244), "The same holds for all of the other models in this study.", fontsize=10)
    document.save(path)
    return path


def test_a_display_formula_becomes_a_formula_and_inline_math_stays_in_the_sentence(tmp_path):
    source = _formula_pdf(tmp_path / "formula.pdf")
    before = source.read_bytes()
    result = _tag(source, tmp_path / "out.pdf")
    assert result.elements["Formula"] == 1
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        formula = _elements(pdf, "Formula")[0]
        assert "/Alt" not in formula                                   # written by the 7.7-1 fix
        x0, y0, x1, y1 = (float(value) for value in formula.A.BBox)
        assert 195 < x0 < 205 and 510 < x1 < 525 and 842 - 205 < y0 < y1 < 842 - 185
        marks = _marks(pdf)
        assert marks[("text", "/Formula")] == 2                        # the formula and its number
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.layout import Layout
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        texts = [" ".join((Layout(pdf).text(p) or "").split()) for p in _elements(pdf, "P")]
        assert any(text.startswith("where α is the offset") for text in texts)   # inline math stays text
        assert not any("y = α" in text for text in texts)
    assert compare_glyph_positions(before, str(tmp_path / "out.pdf")) is None
    assert compare_pages(before, str(tmp_path / "out.pdf"), compare_all=True, check_text=True,
                         strong_tolerance=0.001) is None
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.1-3"] == 0 and rules["7.7-1"] == 1                # the description comes from the 7.7-1 fix


def test_the_formula_fix_without_ai_writes_the_spoken_formula(tmp_path, monkeypatch):
    from pdfaccessguru.LLM.client import settings
    from pdfaccessguru.model.detected_violation import DetectedViolation
    from pdfaccessguru.model.violation import Violation
    from pdfaccessguru.model.violation_category import ViolationCategory
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher import (
        correct_formula_structure_no_alternative_description,
    )

    monkeypatch.setenv("PDFACCESSGURU_AI", "none")
    settings(refresh=True)
    try:
        _tag(_formula_pdf(tmp_path / "formula.pdf"), tmp_path / "tagged.pdf")
        with pikepdf.open(tmp_path / "tagged.pdf") as pdf:
            formula = _elements(pdf, "Formula")[0]
            violation = Violation(category=ViolationCategory.SYNTAX,
                                  name="formula-structure-no-alternative-description", description="", guidelines=[])
            correct_formula_structure_no_alternative_description(
                DetectedViolation(violation=violation, affected_element=formula, supplementary_information=[]), pdf)
            assert str(formula.Alt) == "Equation 1: y equals alpha plus beta times x2"
            pdf.save(tmp_path / "out.pdf")
    finally:
        monkeypatch.delenv("PDFACCESSGURU_AI")
        settings(refresh=True)
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.7-1"] == 0


@pytest.mark.parametrize("text, spoken", [
    ("E = mc^2 (3)", "Equation 3: E equals mc to the power of 2"),
    ("∑ x_i ≤ √ n", "sum of x sub i less than or equal to square root of n"),
    ("α ≠ β, (2a)", "Equation 2a: alpha not equal to beta"),
    ("a ≤ b (1a) c ≥ d (1b)", "Equations 1a and 1b: a less than or equal to b c greater than or equal to d"),
    ("𝑓(𝑥) − 1", "f(x) minus 1"),
    ("\x14 \x15", ""),
    ("I(t)=(cid:88)m[1−sm(t)]gm,(3)", "Equation 3: I(t) equals m[1 minus sm(t)]gm"),   # text from pdfplumber
])
def test_formulas_are_read_aloud_in_words(text, spoken):
    assert formula_spoken_text(text) == spoken
