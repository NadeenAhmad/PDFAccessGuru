"""Phase 6: automatic tagging of PDFs without tags."""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

import fitz
import pikepdf
import pytest

from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.pipeline.pipeline import run_pipeline
from pdfaccessguru.pipeline.transaction import compare_pages
from pdfaccessguru.tagging.builder import tag_document
from pdfaccessguru.tagging.layout import analyse

RESOURCES = Path(__file__).resolve().parents[1] / "resources"


def _untagged_pdf(path: Path, pages: int = 3) -> Path:
    """Pages with a big heading, a paragraph, a bullet list, a picture, and a page number."""
    document = fitz.open()
    picture = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 30), False)
    picture.clear_with(180)
    for number in range(1, pages + 1):
        page = document.new_page(width=595, height=842)
        page.insert_text((72, 90), f"{number} Results of part {number}", fontsize=18, fontname="hebo")
        page.insert_text((72, 130), "The survey shows clearly that the method works for most documents.", fontsize=11)
        page.insert_text((72, 146), "It was tested on many files from different sources and programs.", fontsize=11)
        page.insert_text((90, 180), "• First point of the list", fontsize=11)
        page.insert_text((90, 196), "• Second point of the list", fontsize=11)
        page.insert_image(fitz.Rect(72, 220, 272, 370), pixmap=picture)
        page.insert_text((72, 390), f"Figure {number}: A grey picture", fontsize=10)
        page.insert_text((290, 815), str(number), fontsize=10)
    document.save(path)
    return path


def test_layout_reads_headings_paragraphs_lists_pictures_and_page_numbers(tmp_path):
    with fitz.open(_untagged_pdf(tmp_path / "in.pdf")) as document:
        items = analyse(document)[0]
    kinds = [(item.kind, item.level) for item in items]
    assert kinds[0] == ("H", 1)
    assert [kind for kind, _ in kinds] == ["H", "P", "LI", "LI", "Figure", "Caption", "Artifact"]


def test_tagging_marks_everything_and_keeps_every_page_as_it_was(tmp_path):
    source = _untagged_pdf(tmp_path / "in.pdf")
    before = source.read_bytes()
    with pikepdf.open(source) as pdf:
        result = tag_document(pdf)
        pdf.save(tmp_path / "out.pdf")
    assert result.pages == 3
    assert result.elements["H1"] == 3 and result.elements["L"] == 3 and result.elements["Figure"] == 3
    assert compare_pages(before, str(tmp_path / "out.pdf"), compare_all=True, check_text=True) is None
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.1-3"] == 0 and rules["7.1-11"] == 0             # no untagged content, a tag tree exists


def test_already_tagged_files_are_not_tagged_again(tmp_path):
    source = tmp_path / "tagged.pdf"
    shutil.copy(RESOURCES / "veraPDF_corpus/7.3-t01-fail-a.pdf", source)
    with pikepdf.open(source) as pdf:
        assert tag_document(pdf).pages == 0


def test_pipeline_makes_an_untagged_file_pass_the_check(tmp_path):
    source = _untagged_pdf(tmp_path / "in.pdf")
    before = Counter(v.rule_id for v in run_verapdf(str(source)))
    assert before["7.1-11"] == 1
    run_pipeline(str(source), str(tmp_path / "out.pdf"))
    after = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert after["7.1-11"] == 0 and after["7.1-3"] == 0
    assert sum(after.values()) < sum(before.values())


def _table_pdf(path: Path) -> Path:
    """A paragraph, a ruled table with a header row (3 columns, 3 rows), and a link in the paragraph."""
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 90), "The results are listed in the table below, see the project page.", fontsize=11)
    page.insert_link({"kind": fitz.LINK_URI, "from": fitz.Rect(318, 80, 400, 93), "uri": "https://example.org"})
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
    page.insert_text((72, 230), "The second group was slower but made fewer mistakes overall.", fontsize=11)
    document.save(path)
    return path


def _kids(element):
    kids = element.get("/K")
    return list(kids) if isinstance(kids, pikepdf.Array) else [kids]


def test_tables_get_rows_header_cells_and_data_cells(tmp_path):
    source = _table_pdf(tmp_path / "table.pdf")
    before = source.read_bytes()
    with pikepdf.open(source) as pdf:
        result = tag_document(pdf)
        pdf.save(tmp_path / "out.pdf")
    assert result.elements["Table"] == 1 and result.elements["TH"] == 3 and result.elements["TD"] == 6
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        document = pdf.Root.StructTreeRoot.K[0]
        table = next(kid for kid in _kids(document) if kid.get("/S") == "/Table")
        rows = _kids(table)
        assert [str(row.S) for row in rows] == ["/TR"] * 3
        assert [str(cell.S) for cell in _kids(rows[0])] == ["/TH"] * 3
        assert all(str(cell.S) == "/TD" for row in rows[1:] for cell in _kids(row))
        assert str(_kids(rows[0])[0].A.Scope) == "/Column"
        tags = [str(kid.S) for kid in _kids(document)]
        assert tags.index("/Table") == 1 and tags.count("/P") == 2      # text before, table, text after
    assert compare_pages(before, str(tmp_path / "out.pdf"), compare_all=True, check_text=True) is None
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.1-3"] == 0 and not [rule for rule in rules if rule.startswith("7.2-") and rule != "7.2-34"]


def test_links_are_tagged_inside_the_paragraph_they_are_in(tmp_path):
    source = _table_pdf(tmp_path / "table.pdf")
    with pikepdf.open(source) as pdf:
        assert tag_document(pdf).elements["Link"] == 1
        pdf.save(tmp_path / "out.pdf")
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        annotation = pdf.pages[0].obj.Annots[0]
        nums = list(pdf.Root.StructTreeRoot.ParentTree.Nums)
        keys = nums[0::2]
        assert keys == sorted(keys)
        link = nums[keys.index(annotation.StructParent) * 2 + 1]
        assert str(link.S) == "/Link" and str(link.P.S) == "/P"
        assert link.K[0].Obj.objgen == annotation.objgen
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.18.1-1"] == 0 and rules["7.18.5-1"] == 0


def test_files_whose_tags_cover_almost_no_text_are_tagged_anew(tmp_path):
    """Like a thesis template that tags only the title page: the old tags are replaced."""
    title = fitz.open()
    title.new_page(width=595, height=842).insert_text((72, 90), "Thesis", fontsize=18)
    title.save(tmp_path / "title.pdf")
    with pikepdf.open(tmp_path / "title.pdf") as pdf, pikepdf.open(_untagged_pdf(tmp_path / "body.pdf", pages=12)) as body:
        tag_document(pdf)
        pdf.pages.extend(body.pages)
        pdf.save(tmp_path / "mixed.pdf")
    with pikepdf.open(tmp_path / "mixed.pdf") as pdf:
        result = tag_document(pdf)
        pdf.save(tmp_path / "out.pdf")
    assert result.replaced_share is not None and result.replaced_share < 0.05
    assert result.pages == 13 and result.elements["H1"] >= 12
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.1-3"] == 0


def test_merged_cells_get_row_spans_and_broken_grids_stay_text(tmp_path):
    """A first-column cell merged over two rows gets RowSpan 2; the rows stay equally wide."""
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    left, top, width, height = 72, 100, 150, 24
    for r in range(4):                                     # header line, then rows 1-3; no line between rows 2 and 3 in column 1
        x0 = left + width if r == 3 else left
        page.draw_line((x0, top + r * height), (left + 3 * width, top + r * height))
    page.draw_line((left, top + 4 * height), (left + 3 * width, top + 4 * height))
    page.draw_line((left + width, top + 3 * height), (left + 3 * width, top + 3 * height))
    for c in range(4):
        page.draw_line((left + c * width, top), (left + c * width, top + 4 * height))
    texts = {(0, 0): "Group", (0, 1): "Day", (0, 2): "Result", (1, 0): "A", (1, 1): "Monday", (1, 2): "Good",
             (2, 0): "B", (2, 1): "Monday", (2, 2): "Fair", (3, 1): "Tuesday", (3, 2): "Good"}
    for (r, c), text in texts.items():
        page.insert_text((left + c * width + 6, top + r * height + 16), text, fontsize=11)
    document.save(tmp_path / "merged.pdf")
    with pikepdf.open(tmp_path / "merged.pdf") as pdf:
        result = tag_document(pdf)
        pdf.save(tmp_path / "out.pdf")
    assert result.elements["Table"] == 1 and result.elements["TH"] + result.elements["TD"] == 11
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        table = pdf.Root.StructTreeRoot.K[0].K[0]
        merged = _kids(_kids(table)[2])[0]
        assert int(merged.A.RowSpan) == 2
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.2-42"] == 0 and rules["7.2-43"] == 0 and rules["7.1-3"] == 0

    from pdfaccessguru.tagging.layout import _is_regular, Item
    overlapping = [Item("Cell", 0, fitz.Rect(), row=0, col=0, col_span=2), Item("Cell", 0, fitz.Rect(), row=0, col=1)]
    assert not _is_regular(overlapping, 1, 2)


def test_tagging_anew_also_removes_old_tags_inside_forms(tmp_path):
    """Old MCIDs inside form XObjects would end up inside decoration after re-tagging (rule 7.1-2)."""
    from pdfaccessguru.tagging.builder import strip_tags

    source = _untagged_pdf(tmp_path / "in.pdf", pages=1)
    with pikepdf.open(source) as pdf:
        form = pdf.make_stream(b"/P <</MCID 5>> BDC 0 0 m 10 10 l S EMC /Artifact BMC 0 0 m 5 5 l S EMC",
                               Type=pikepdf.Name.XObject, Subtype=pikepdf.Name.Form, BBox=[0, 0, 10, 10],
                               StructParents=7)
        pdf.pages[0].obj.Resources.XObject = pikepdf.Dictionary(Fm9=form)
        pdf.Root.StructTreeRoot = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.StructTreeRoot))
        strip_tags(pdf)
        assert b"MCID" not in form.read_bytes() and b"Artifact" in form.read_bytes()
        assert "/StructParents" not in form
