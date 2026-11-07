"""
Tests of the group-level structure repairs (lists, tables, tables of contents, headings).

Small tagged PDFs are built here with text at known positions, so the tests can check that
whole groups are rebuilt the way a person would: cells on one line form one row, consecutive
items form one list, every heading stays a heading.
"""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

import pikepdf
import pytest
from pikepdf import Array, Dictionary, Name

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.lists import ListRepair, looks_like_marker
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tables import CellsWithoutRows, TableRepair
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.toc_and_headings import (
    repair_headings, repair_toc, repair_toc_parent,
)
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import kids, parent_tree_owner
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.pipeline.pipeline import run_pipeline

RESOURCES = Path(__file__).resolve().parents[1] / "resources"


# --- building small tagged PDFs ------------------------------------------------------------

def build(spec, path: Path | None = None) -> pikepdf.Pdf:
    """
    A one-page tagged PDF from a nested spec. ("Table", [children]) makes an element with
    children; ("TD", "text", (x, y)) makes an element showing the text at that position;
    ("TD", None) makes an empty element; an int n is loose marked content of the parent, shown
    at (300, 700 - 20 * n). MCIDs are numbered in the order the content is created.
    """
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    page = pdf.pages[0]
    font = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica,
                                        Encoding=Name.WinAnsiEncoding))
    page.obj["/Resources"] = Dictionary(Font=Dictionary(F1=font))
    page.obj["/StructParents"] = 0
    content: list[str] = []
    owners: list = []

    def show(tag: str, text: str, x: float, y: float, owner) -> int:
        mcid = len(owners)
        owners.append(owner)
        text = text.replace("\u2022", "\x95")            # the bullet in WinAnsiEncoding
        content.append(f"/{tag} <</MCID {mcid}>> BDC BT /F1 10 Tf {x} {y} Td ({text}) Tj ET EMC")
        return mcid

    def make(node, parent):
        if isinstance(node, int):
            return show("Span", f"mcid{node}", 300, 700 - 20 * node, parent)
        tag, body = node[0], node[1]
        element = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name("/" + tag), P=parent, Pg=page.obj))
        if isinstance(body, list):
            element["/K"] = Array([make(child, element) for child in body])
        elif body is not None:
            x, y = node[2]
            element["/K"] = Array([show(tag, body, x, y, element)])
        return element

    root = pdf.make_indirect(Dictionary(Type=Name.StructTreeRoot))
    document = make(spec, root)
    root["/K"] = Array([document])
    root["/ParentTree"] = pdf.make_indirect(Dictionary(Nums=Array([0, Array(owners)])))
    root["/ParentTreeNextKey"] = 1
    pdf.Root["/StructTreeRoot"] = root
    pdf.Root["/MarkInfo"] = Dictionary(Marked=True)
    page.obj["/Contents"] = pdf.make_stream("\n".join(content).encode("latin-1"))
    if path is not None:
        pdf.save(path)
        return pikepdf.open(path)
    return pdf


def tags(element) -> list:
    """The tree below an element as nested [tag, children] lists (MCIDs as ints)."""
    result = []
    for kid in kids(element):
        if isinstance(kid, Dictionary) and "/S" in kid:
            inner = tags(kid)
            result.append([str(kid.S)[1:], inner] if inner and not all(isinstance(i, int) for i in inner) else str(kid.S)[1:])
        elif isinstance(kid, int):
            result.append(kid)
    return result


def first(pdf, tag: str):
    for obj in pdf.objects:
        if isinstance(obj, Dictionary) and obj.get("/S") == Name("/" + tag):
            return obj
    raise AssertionError(f"no {tag}")


def cell(text, x, y, tag="TD"):
    return (tag, text, (x, y))


# --- tables ---------------------------------------------------------------------------------

def test_loose_cells_become_rows_by_their_line_on_the_page(tmp_path):
    grid = [cell(f"r{r}c{c}", 100 + 120 * c, 600 - 30 * r) for r in range(2) for c in range(3)]
    pdf = build(("Document", [("Table", [("TBody", grid)])]), tmp_path / "grid.pdf")
    body = first(pdf, "TBody")

    assert TableRepair(pdf).repair_group(body)

    assert tags(body) == [["TR", ["TD", "TD", "TD"]], ["TR", ["TD", "TD", "TD"]]]
    pdf.save(tmp_path / "out.pdf")
    assert not {"7.2-37", "7.2-9", "7.2-42", "7.2-43"} & {v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf"))}


def test_without_positions_rows_get_the_column_count_of_the_other_rows():
    pdf = build(("Document", [("Table", [
        ("THead", [("TR", [cell("a", 100, 700, "TH"), cell("b", 200, 700, "TH")])]),
        ("TBody", [("TD", None), ("TD", None), ("TD", None), ("TD", None)]),
    ])]))
    body = first(pdf, "TBody")
    # empty cells have no position; give them content without position (alternate text)
    for td in kids(body):
        td["/ActualText"] = pikepdf.String("x")

    TableRepair(pdf).repair_group(body)

    assert tags(body) == [["TR", ["TD", "TD"]], ["TR", ["TD", "TD"]]]


def test_cells_whose_rows_cannot_be_worked_out_are_left_alone():
    pdf = build(("Document", [("Table", [("TBody", [("TD", None), ("TD", None), ("TD", None)])])]))
    body = first(pdf, "TBody")
    for td in kids(body):
        td["/ActualText"] = pikepdf.String("x")
    with pytest.raises(CellsWithoutRows):
        TableRepair(pdf).repair_group(body)
    assert tags(body) == ["TD", "TD", "TD"]


def test_a_loose_cell_on_the_line_of_a_row_joins_that_row():
    pdf = build(("Document", [("Table", [("TBody", [
        ("TR", [cell("a", 100, 600)]), cell("b", 220, 600), ("TR", [cell("c", 100, 570), cell("d", 220, 570)]),
    ])])]))
    body = first(pdf, "TBody")
    TableRepair(pdf).repair_group(body)
    assert tags(body) == [["TR", ["TD", "TD"]], ["TR", ["TD", "TD"]]]


def test_text_inside_a_cell_area_joins_the_cell_and_a_full_row_keeps_its_columns():
    pdf = build(("Document", [("Table", [("TBody", [
        ("TR", [cell("first cell text", 100, 600), cell("second", 300, 600), ("Span", "more", (140, 600))]),
        ("TR", [cell("c", 100, 570), cell("d", 300, 570)]),
    ])])]))
    row = kids(first(pdf, "TBody"))[0]
    TableRepair(pdf).repair_row(row)
    assert tags(row) == [["TD", [0, "Span"]], "TD"]               # still two columns


def test_paragraphs_in_a_row_without_cells_become_one_cell_each():
    pdf = build(("Document", [("Table", [("TR", [("P", "a", (100, 600)), ("P", "b", (300, 600))])])]))
    row = first(pdf, "TR")
    TableRepair(pdf).repair_row(row)
    assert tags(row) == [["TD", ["P"]], ["TD", ["P"]]]


def test_text_in_the_middle_of_a_table_becomes_a_row_across_all_columns():
    pdf = build(("Document", [("Table", [
        ("TR", [cell("a", 100, 600), cell("b", 300, 600)]),
        ("P", "Subtotals", (100, 570)),
        ("TR", [cell("c", 100, 540), cell("d", 300, 540)]),
    ])]))
    table = first(pdf, "Table")
    TableRepair(pdf).repair_group(table)
    middle = kids(table)[1]
    assert tags(table)[1] == ["TR", [["TD", ["P"]]]]
    assert int(kids(middle)[0].A.ColSpan) == 2


def test_caption_like_text_becomes_the_caption_and_other_text_moves_out_of_the_table():
    pdf = build(("Document", [
        ("Table", [
            ("P", "Table 2: Results", (100, 640)),
            ("TR", [cell("a", 100, 600), cell("b", 300, 600)]),
            ("P", "Source: own survey", (100, 560)),
        ]),
    ]))
    table = first(pdf, "Table")
    TableRepair(pdf).repair_group(table)
    assert tags(table) == ["Caption", ["TR", ["TD", "TD"]]]
    assert tags(table.P) == [["Table", ["Caption", ["TR", ["TD", "TD"]]]], "P"]   # reading order kept


def test_empty_tags_are_removed_and_grouping_tags_around_rows_are_unwrapped():
    pdf = build(("Document", [("Table", [
        ("Div", [("TR", [cell("a", 100, 600)]), ("TR", [cell("b", 100, 570)])]),
        ("Span", None),
    ])]))
    table = first(pdf, "Table")
    TableRepair(pdf).repair_group(table)
    assert tags(table) == [["TR", ["TD"]], ["TR", ["TD"]]]


# --- lists ----------------------------------------------------------------------------------

def item(n, y):
    return ("LI", [("Lbl", "-", (90, y)), ("LBody", f"item {n}", (100, y))])


def test_consecutive_loose_items_form_one_list_and_items_after_a_list_join_it():
    pdf = build(("Document", [("P", "intro", (90, 700)), item(1, 680), item(2, 660),
                              ("P", "between", (90, 640)),
                              ("L", [item(3, 620)]), item(4, 600)]))
    document = first(pdf, "Document")
    ListRepair(pdf).repair_parent(document)
    assert [t if isinstance(t, str) else t[0] for t in tags(document)] == ["P", "L", "P", "L"]
    first_list, second_list = [k for k in kids(document) if k.S == Name.L]
    assert len(kids(first_list)) == 2 and len(kids(second_list)) == 2


def test_label_and_body_stay_together():
    pdf = build(("Document", [("L", [("Lbl", "1.", (90, 680)), ("LBody", "first", (100, 680)),
                                     ("Lbl", "2.", (90, 660)), ("LBody", "second", (100, 660))])]))
    lst = first(pdf, "L")
    ListRepair(pdf).repair_list(lst)
    assert tags(lst) == [["LI", ["Lbl", "LBody"]], ["LI", ["Lbl", "LBody"]]]


def test_paragraphs_in_a_list_become_items_and_continuation_text_joins_its_item():
    pdf = build(("Document", [("L", [item(1, 680), ("P", "continues item one", (100, 670)),
                                     ("P", "• a new item", (90, 650))])]))
    lst = first(pdf, "L")
    ListRepair(pdf).repair_list(lst)
    assert tags(lst) == [["LI", ["Lbl", ["LBody", [1, "P"]]]], ["LI", [["LBody", ["P"]]]]]


def test_a_list_of_paragraphs_gets_one_item_per_paragraph():
    pdf = build(("Document", [("L", [("P", "one", (90, 680)), ("P", "two", (90, 660)), ("P", "three", (90, 640))])]))
    lst = first(pdf, "L")
    ListRepair(pdf).repair_list(lst)
    assert len(kids(lst)) == 3 and all(k.S == Name.LI for k in kids(lst))


def test_a_bullet_tagged_as_span_becomes_the_label():
    pdf = build(("Document", [("L", [("LI", [("Span", "•", (90, 680)), ("LBody", "text", (100, 680)),
                                             ("Figure", "img", (300, 680))])])]))
    li = first(pdf, "LI")
    ListRepair(pdf).repair_item(li)
    assert tags(li) == ["Lbl", ["LBody", [1, "Figure"]]]


@pytest.mark.parametrize("text, expected", [("•", True), ("1.", True), ("a)", True), ("(iv)", True),
                                            ("-", True), ("Results", False), ("2024", False)])
def test_list_markers(text, expected):
    assert looks_like_marker(text) is expected


# --- tables of contents ---------------------------------------------------------------------

def test_loose_entries_form_one_toc_or_join_the_toc_next_to_them():
    pdf = build(("Document", [("TOCI", "1 Intro", (90, 700)), ("TOCI", "2 Method", (90, 680)),
                              ("P", "text", (90, 600)),
                              ("TOCI", "3 Results", (90, 580)), ("TOC", [("TOCI", "4 End", (90, 560))])]))
    document = first(pdf, "Document")
    repair_toc_parent(pdf, document)
    assert tags(document) == [["TOC", ["TOCI", "TOCI"]], "P", ["TOC", ["TOCI", "TOCI"]]]


def test_a_page_number_outside_its_entry_joins_the_entry():
    pdf = build(("Document", [("TOC", [("TOCI", [("Reference", "Intro", (90, 700))]), ("Span", "3", (500, 700)),
                                       ("Reference", "Method", (90, 680)), 1])]))
    toc = first(pdf, "TOC")
    repair_toc(pdf, toc)
    assert tags(toc) == [["TOCI", ["Reference", "Span"]], ["TOCI", ["Reference", 3]]]
    page = pdf.pages[0].obj
    assert parent_tree_owner(pdf, page, 3).objgen == kids(toc)[1].objgen      # screen readers find it


# --- headings -------------------------------------------------------------------------------

def test_a_section_with_two_headings_becomes_two_sections_at_the_same_level():
    pdf = build(("Document", [("Sect", [("H", "One", (90, 700)), ("P", "a", (90, 680)),
                                        ("H", "Two", (90, 660)), ("P", "b", (90, 640))])]))
    document = first(pdf, "Document")
    repair_headings(pdf, first(pdf, "Sect"))
    assert tags(document) == [["Sect", ["H", "P"]], ["Sect", ["H", "P"]]]


def test_headings_directly_in_the_document_get_a_section_each_and_loose_content_moves_along():
    pdf = build(("Document", [("P", "front", (90, 720)), ("H", "One", (90, 700)), 2,
                              ("H", "Two", (90, 660)), ("P", "b", (90, 640))]))
    document = first(pdf, "Document")
    repair_headings(pdf, document)
    assert tags(document) == ["P", ["Sect", ["H", 2]], ["Sect", ["H", "P"]]]
    section = kids(document)[1]
    assert parent_tree_owner(pdf, pdf.pages[0].obj, 2).objgen == section.objgen


# --- the whole pipeline on veraPDF's test files ---------------------------------------------------

@pytest.mark.parametrize("name, rules", [
    ("veraPDF_corpus/7.2-t03-fail-a.pdf", {"7.2-3"}),
    ("veraPDF_corpus/7.2-t08-fail-a.pdf", {"7.2-8", "7.2-36"}),
    ("veraPDF_corpus/7.2-t10-fail-a.pdf", {"7.2-10"}),
    ("veraPDF_corpus/7.2-t17-fail-a.pdf", {"7.2-17"}),
    ("veraPDF_corpus/7.2-t18-fail-a.pdf", {"7.2-18"}),
    ("veraPDF_corpus/7.2-t19-fail-b.pdf", {"7.2-19"}),
    ("veraPDF_corpus/7.2-t20-fail-a.pdf", {"7.2-20"}),
    ("veraPDF_corpus/7.2-t26-fail-a.pdf", {"7.2-26"}),
    ("veraPDF_corpus/7.2-t36-fail-a.pdf", {"7.2-36"}),
    ("veraPDF_corpus/7.2-t37-fail-a.pdf", {"7.2-37"}),
    ("veraPDF_corpus/7.2-t38-fail-a.pdf", {"7.2-38"}),
    ("veraPDF_corpus/7.4.4-t01-fail-a.pdf", {"7.4.4-1"}),
    ("PDFAccessGuru_corpus/7.2-t09-fail-b.pdf", {"7.2-9", "7.2-37", "7.2-43"}),
])
def test_pipeline_fixes_the_whole_group_without_new_problems(tmp_path, name, rules):
    source = tmp_path / Path(name).name
    shutil.copy(RESOURCES / name, source)
    before = Counter(v.rule_id for v in run_verapdf(str(source)))
    assert rules <= set(before)

    run_pipeline(str(source), str(tmp_path / "out.pdf"))

    after = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert not rules & set(after)
    assert sum(after.values()) < sum(before.values())


def test_pipeline_keeps_every_heading_of_the_corpus_file(tmp_path):
    source = tmp_path / "h.pdf"
    shutil.copy(RESOURCES / "veraPDF_corpus/7.4.4-t01-fail-a.pdf", source)
    run_pipeline(str(source), str(tmp_path / "out.pdf"))
    with pikepdf.open(source) as before, pikepdf.open(tmp_path / "out.pdf") as after:
        def headings(pdf):
            return sum(1 for o in pdf.objects if isinstance(o, Dictionary) and o.get("/S") == Name.H)
        assert headings(after) == headings(before) == 2


# --- content marked as decoration and tagged at the same time (rule 7.1-2) ----------------------------

def _page_with_content(content: bytes, tag: str):
    """A page whose content is given; one structure element of the given type owns MCID 0."""
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    page = pdf.pages[0].obj
    font = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica))
    page["/Resources"] = Dictionary(Font=Dictionary(F1=font))
    page["/StructParents"] = 0
    page["/Contents"] = pdf.make_stream(content)
    root = pdf.make_indirect(Dictionary(Type=Name.StructTreeRoot))
    document = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.Document, P=root, Pg=page))
    owner = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name("/" + tag), P=document, Pg=page, K=0))
    document["/K"] = Array([owner])
    root["/K"] = Array([document])
    root["/ParentTree"] = pdf.make_indirect(Dictionary(Nums=Array([0, Array([owner])])))
    pdf.Root["/StructTreeRoot"] = root
    return pdf, owner


def _operators(pdf) -> list[str]:
    return [f"{op}:{operands[0]}" if str(op) in ("BDC", "BMC") else str(op)
            for operands, op in pikepdf.parse_content_stream(pdf.pages[0])]


def test_decoration_with_a_paragraph_tag_becomes_real_content():
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.artifacts import fix_tagged_artifacts
    pdf, owner = _page_with_content(b"/Artifact <</MCID 0 /Type /Pagination>> BDC BT /F1 9 Tf 72 40 Td (Page 1) Tj ET EMC", "P")
    result = fix_tagged_artifacts(pdf, pdf.pages[0])
    assert result.made_content == 1
    assert _operators(pdf)[0] == "BDC:/P"
    assert parent_tree_owner(pdf, pdf.pages[0].obj, 0).objgen == owner.objgen


def test_decoration_with_a_tag_named_artifact_stays_decoration_and_the_tag_goes():
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.artifacts import fix_tagged_artifacts
    pdf, owner = _page_with_content(b"/Artifact <</MCID 0>> BDC 0 0 10 10 re f EMC", "Artifact")
    result = fix_tagged_artifacts(pdf, pdf.pages[0])
    assert result.kept_decoration == 1
    assert _operators(pdf)[0] == "BMC:/Artifact"
    assert kids(pdf.Root.StructTreeRoot.K[0]) == []                       # the empty tag is removed
    assert parent_tree_owner(pdf, pdf.pages[0].obj, 0) is None


def test_tagged_text_inside_a_footer_keeps_its_tag_and_the_drawing_stays_decoration():
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.artifacts import fix_tagged_artifacts
    pdf, _ = _page_with_content(
        b"/Artifact <</Type /Pagination>> BDC BT /Note <</MCID 0>> BDC /F1 9 Tf 72 40 Td (1 See page 3) Tj EMC ET "
        b"72 52 100 0.5 re f EMC", "Note")
    fix_tagged_artifacts(pdf, pdf.pages[0])
    assert _operators(pdf) == ["BT", "BDC:/Note", "Tf", "Td", "Tj", "EMC", "ET", "BDC:/Artifact", "re", "f", "EMC"]
