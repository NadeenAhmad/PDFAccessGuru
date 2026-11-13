"""Phase 6, v1.1: headings, heading levels, lists and captions of the automatic tagger."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pymupdf as fitz
import pikepdf

from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.pipeline.transaction import compare_pages
from pdfaccessguru.tagging.builder import tag_document
from pdfaccessguru.tagging.layout import analyse


def _kids(element) -> list:
    kids = element.get("/K")
    if kids is None:
        return []
    return list(kids) if isinstance(kids, pikepdf.Array) else [kids]


def _elements(element) -> list:
    return [kid for kid in _kids(element) if isinstance(kid, pikepdf.Dictionary)]


def _tag(source: Path, target: Path) -> tuple[Counter, list]:
    """Tag a file; returns the element counts and the children of the Document element."""
    before = source.read_bytes()
    with pikepdf.open(source) as pdf:
        result = tag_document(pdf)
        pdf.save(target)
    assert compare_pages(before, str(target), compare_all=True, check_text=True) is None
    with pikepdf.open(target) as pdf:
        tags = [str(kid.S) for kid in _elements(pdf.Root.StructTreeRoot.K[0])]
    return result.elements, tags


def _paragraph(page, top: float, lines: list[str], left: float = 72, size: float = 11, font: str = "helv") -> float:
    for line in lines:
        page.insert_text((left, top), line, fontsize=size, fontname=font)
        top += size * 1.35
    return top


BODY = ["The survey shows clearly that the method works for most of the documents we had.",
        "It was tested on many files from different sources and programs over two years.",
        "Most of the files were reports, papers and forms written by public authorities."]


def test_long_bold_paragraph_is_not_a_heading(tmp_path):
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 80), "Results of the survey", fontsize=11, fontname="hebo")
    _paragraph(page, 110, BODY)
    bold = ["This whole paragraph is written in bold type because the authors wanted to stress it, but",
            "it is still a paragraph with several sentences and not a heading. It goes on for three lines",
            "and ends like every sentence does, with a full stop at the end of it."]
    _paragraph(page, 180, bold, font="hebo")
    _paragraph(page, 260, ["This line is set in a larger type to stand out from the rest", "of the page, yet it is no heading at all."],
               size=14)
    _paragraph(page, 320, BODY)
    page.insert_text((30, 700), "arXiv:2003.05924v4 [physics.soc-ph] 29 Jan 2021", fontsize=20, rotate=90)
    document.save(tmp_path / "in.pdf")
    with fitz.open(tmp_path / "in.pdf") as pdf:
        items = analyse(pdf)[0]
    kinds = {item.text[:20]: item.kind for item in items}
    assert kinds["Results of the surve"] == "H"
    assert kinds["This whole paragraph"] == "P"
    assert kinds["This line is set in "] == "P"
    assert kinds["arXiv:2003.05924v4 ["] == "P"                    # a stamp along the margin
    assert all(len(item.text) <= 150 for item in items if item.kind == "H")


def test_heading_levels_follow_numbering_and_never_skip_a_level(tmp_path):
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    headings = [("A Study of Something Important", 20, "hebo"), ("Abstract", 12, "hebo"),
                ("1 Introduction", 14, "hebo"), ("1.1 Background", 12, "hebo"), ("2 Methods", 14, "hebo"),
                ("2.1.1 A deeper section", 11, "hebo"), ("References", 14, "hebo")]
    top = 70.0
    for text, size, font in headings:
        page.insert_text((72, top), text, fontsize=size, fontname=font)
        top = _paragraph(page, top + 24, BODY[:2]) + 18
    document.save(tmp_path / "in.pdf")
    elements, tags = _tag(tmp_path / "in.pdf", tmp_path / "out.pdf")
    levels = [int(tag[2]) for tag in tags if tag.startswith("/H")]
    assert levels == [1, 2, 2, 3, 2, 3, 2]
    assert levels[0] == 1 and all(b <= a + 1 for a, b in zip(levels, levels[1:]))


def test_bullet_list_with_a_symbol_font_marker_gets_label_and_body(tmp_path):
    """Bullets drawn on their own in the Symbol font, left of the text: L > LI > (Lbl, LBody)."""
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    top = _paragraph(page, 80, ["Specific opportunities include:"])
    entries = [["Space heating, including district heating. Data center heat can be collected",
                "and distributed to residential buildings nearby."],
               ["Food and beverage processing."],
               ["Water distillation and treatment."]]
    for entry in entries:
        page.insert_text((90, top + 6), "•", fontsize=11, fontname="symb")
        top = _paragraph(page, top + 6, entry, left=108)
    _paragraph(page, top + 20, BODY)
    document.save(tmp_path / "in.pdf")
    elements, tags = _tag(tmp_path / "in.pdf", tmp_path / "out.pdf")
    assert tags == ["/P", "/L", "/P"]
    assert elements["LI"] == 3 and elements["Lbl"] == 3
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        items = _elements(_elements(pdf.Root.StructTreeRoot.K[0])[1])
        assert [[str(part.S) for part in _elements(item)] for item in items] == [["/Lbl", "/LBody"]] * 3
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.1-3"] == 0 and rules["7.2-19"] == 0 and rules["7.2-20"] == 0


def test_numbered_reference_list_becomes_a_list_but_numbered_text_does_not(tmp_path):
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 80), "2 Methods", fontsize=14, fontname="hebo")
    top = _paragraph(page, 110, ["(1) the first reason is given here in a paragraph that starts with a number,",
                                 "and it simply goes on as normal text; no list follows it at all."])
    top = _paragraph(page, top + 10, ["As shown in the work by Kumar and colleagues in their study of",
                                      "[12] and later work, documents are rarely accessible."])
    page.insert_text((72, top + 20), "References", fontsize=14, fontname="hebo")
    top += 50
    references = [["Kermack, W. O. and McKendrick, A. G. A contribution to the mathematical",
                   "theory of epidemics. Proc. R. Soc. A 115, 700-721 (1927)."],
                  ["Diekmann, O. and Heesterbeek, J. A. P. Mathematical epidemiology (2000)."],
                  ["Newman, M. E. J. Spread of epidemic disease on networks. Phys. Rev. E 66",
                   "(2002)."]]
    for number, reference in enumerate(references, start=1):
        page.insert_text((72, top), f"[{number}]", fontsize=10)
        top = _paragraph(page, top, reference, left=92, size=10) + 2
    document.save(tmp_path / "in.pdf")
    with fitz.open(tmp_path / "in.pdf") as pdf:
        kinds = [(item.kind, item.text[:12]) for item in analyse(pdf)[0]]
    assert kinds[0] == ("H", "2 Methods")
    assert [kind for kind, _ in kinds[1:3]] == ["P", "P"]
    elements, tags = _tag(tmp_path / "in.pdf", tmp_path / "out.pdf")
    assert tags == ["/H1", "/P", "/P", "/H1", "/L"]
    assert elements["LI"] == 3 and elements["Lbl"] == 3


def test_nested_list_goes_inside_the_body_of_its_item(tmp_path):
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    top = _paragraph(page, 80, ["We bought the following things at the market this week:"])
    for left, text in [(72, "• Fruit from the farm stand"), (92, "- Apples from the old tree"),
                       (92, "- Pears that were nearly ripe"), (72, "• Vegetables for the soup")]:
        top = _paragraph(page, top + 4, [text], left=left)
    _paragraph(page, top + 20, BODY)
    document.save(tmp_path / "in.pdf")
    elements, tags = _tag(tmp_path / "in.pdf", tmp_path / "out.pdf")
    assert tags == ["/P", "/L", "/P"] and elements["L"] == 2 and elements["LI"] == 4
    assert elements["Lbl"] == 0                  # each marker is shown with its text: the whole line is the body
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        outer = _elements(pdf.Root.StructTreeRoot.K[0])[1]
        items = _elements(outer)
        assert [str(item.S) for item in items] == ["/LI", "/LI"]
        body = _elements(items[0])[-1]
        assert str(body.S) == "/LBody"
        nested = [kid for kid in _elements(body) if str(kid.S) == "/L"]
        assert len(nested) == 1 and len(_elements(nested[0])) == 2
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.1-3"] == 0 and rules["7.2-19"] == 0 and rules["7.2-20"] == 0


def test_table_caption_is_the_first_child_of_its_table(tmp_path):
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    _paragraph(page, 80, BODY[:1])
    page.insert_text((72, 112), "Table 1: Results of both groups", fontsize=10)
    rows = [["Measure", "Group A", "Group B"], ["Time (min)", "1:41", "2:05"], ["Errors", "3", "5"]]
    left, top, width, height = 72, 120, 150, 24
    for r in range(len(rows) + 1):
        page.draw_line((left, top + r * height), (left + 3 * width, top + r * height))
    for c in range(4):
        page.draw_line((left + c * width, top), (left + c * width, top + len(rows) * height))
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            page.insert_text((left + c * width + 6, top + r * height + 16), text, fontsize=11,
                             fontname="hebo" if r == 0 else "helv")
    _paragraph(page, 230, BODY[1:])
    document.save(tmp_path / "in.pdf")
    elements, tags = _tag(tmp_path / "in.pdf", tmp_path / "out.pdf")
    assert tags == ["/P", "/Table", "/P"] and elements["Caption"] == 1
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        table = _elements(pdf.Root.StructTreeRoot.K[0])[1]
        assert [str(kid.S) for kid in _elements(table)] == ["/Caption", "/TR", "/TR", "/TR"]
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.2-16"] == 0 and rules["7.1-3"] == 0


def test_figure_caption_is_read_right_after_its_figure_not_inside_it(tmp_path):
    """Two columns; the figure and its two-line caption sit in the right column."""
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    picture = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 30), False)
    picture.clear_with(180)
    column = ["Text in the left column of the page that", "goes on for a while and explains things",
              "that the reader needs to know about it."]
    top = 80.0
    for _ in range(4):
        top = _paragraph(page, top, column, left=50, size=10) + 10
    page.insert_image(fitz.Rect(310, 70, 540, 200), pixmap=picture)
    _paragraph(page, 215, ["Figure 1: A grey picture of the setup that", "we used in the second study."],
               left=310, size=9)
    _paragraph(page, 260, ["Figure 2 shows that the setup works well in", "the right column of the page too."],
               left=310, size=10)
    document.save(tmp_path / "in.pdf")
    with fitz.open(tmp_path / "in.pdf") as pdf:
        items = analyse(pdf)[0]
    kinds = [item.kind for item in items]
    assert kinds.count("Caption") == 1
    figure = kinds.index("Figure")
    assert kinds[figure + 1] == "Caption" and "second study" in items[figure + 1].text
    assert kinds[:figure] == ["P"] * 4                        # the left column is read first
    elements, tags = _tag(tmp_path / "in.pdf", tmp_path / "out.pdf")
    assert tags == ["/P"] * 4 + ["/Figure", "/Caption", "/P"]
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        figure_element = _elements(pdf.Root.StructTreeRoot.K[0])[4]
        assert not [kid for kid in _elements(figure_element) if str(kid.S) == "/Caption"]


def test_captions_are_told_apart_from_sentences_that_mention_a_figure(tmp_path):
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    texts = ["Abbildung 2: Aufbau der Anlage im Labor", "Tabelle 3 zeigt die Ergebnisse der Messung im Detail.",
             "Fig. 4 Overview of the whole system", "Figure 5a shows the effect of noise on the system.",
             "Listing 1: The main loop of the program", "Tab. 2. Results of the second group"]
    top = 80.0
    for text in texts:
        top = _paragraph(page, top, [text]) + 30
    document.save(tmp_path / "in.pdf")
    with fitz.open(tmp_path / "in.pdf") as pdf:
        kinds = [item.kind for item in analyse(pdf)[0]]
    assert kinds == ["Caption", "P", "Caption", "P", "Caption", "Caption"]
