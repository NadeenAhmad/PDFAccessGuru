"""
1.1: content that a partly tagged file left untagged gets its place in the existing tag tree.

The PDFs are built here: pages whose heading and first paragraph are tagged (like a template
that tagged part of the paper), with an untagged running header, paragraph, picture, thin
line and page number.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pikepdf
import pymupdf as fitz
from pikepdf import Array, Dictionary, Name

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import kids
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.pipeline.pipeline import run_pipeline
from pdfaccessguru.pipeline.text_tagging import measure_text_tagging
from pdfaccessguru.pipeline.transaction import compare_glyph_positions, compare_pages
from pdfaccessguru.tagging.leftovers import tag_leftovers

UNTAGGED_PARAGRAPH = ("BT /F1 11 Tf 72 640 Td (This paragraph was left untagged by the template.) Tj "
                      "0 -14 Td (It continues on a second line of the same paragraph.) Tj ET")


def _page_content(number: int, tagged: bool, extra: str = "") -> str:
    header = "BT /F1 9 Tf 72 770 Td (Journal of Testing 2026) Tj ET"
    heading = f"BT /F1 18 Tf 72 700 Td ({number} Introduction) Tj ET"
    paragraph = "BT /F1 11 Tf 72 670 Td (The tagged paragraph explains the method in detail.) Tj ET"
    if tagged:
        heading = f"/H1 <</MCID 0>> BDC {heading} EMC"
        paragraph = f"/P <</MCID 1>> BDC {paragraph} EMC"
    return "\n".join([
        header, heading, paragraph, UNTAGGED_PARAGRAPH,
        "q 120 0 0 90 72 480 cm /Im1 Do Q",                  # a picture
        "q 400 0 0 2 72 460 cm /Im1 Do Q",                   # a thin line drawn as a picture
        extra,
        f"BT /F1 10 Tf 300 30 Td ({number}) Tj ET",          # the page number
    ])


def partly_tagged(path: Path, pages: int = 2, untagged_pages: tuple[int, ...] = (), kids_tree: bool = False,
                  extra: dict[int, str] | None = None) -> Path:
    """Pages whose heading and first paragraph are tagged; the rest of each page is not."""
    pdf = pikepdf.new()
    font = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica,
                                        Encoding=Name.WinAnsiEncoding))
    picture = pdf.make_stream(b"\x60\x90\xb0\x70", Type=Name.XObject, Subtype=Name.Image, Width=2, Height=2,
                              ColorSpace=Name.DeviceGray, BitsPerComponent=8)
    root = pdf.make_indirect(Dictionary(Type=Name.StructTreeRoot))
    document = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.Document, P=root))
    children, entries, key = [], [], 0
    for number in range(1, pages + 1):
        pdf.add_blank_page(page_size=(612, 792))
        page = pdf.pages[-1]
        page.obj["/Resources"] = Dictionary(Font=Dictionary(F1=font), XObject=Dictionary(Im1=picture))
        tagged = number - 1 not in untagged_pages
        content = _page_content(number, tagged, (extra or {}).get(number - 1, ""))
        page.obj["/Contents"] = pdf.make_stream(content.encode("latin-1"))
        if tagged:
            heading = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.H1, P=document, Pg=page.obj, K=Array([0])))
            paragraph = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.P, P=document, Pg=page.obj, K=Array([1])))
            children += [heading, paragraph]
            page.obj["/StructParents"] = key
            entries.append((key, Array([heading, paragraph])))
            key += 1
    document["/K"] = Array(children)
    root["/K"] = Array([document])
    if kids_tree:          # a number tree split into two leaves
        middle = max(1, len(entries) // 2)
        leaves = [pdf.make_indirect(Dictionary(Nums=Array([v for entry in part for v in entry]),
                                               Limits=Array([part[0][0], part[-1][0]])))
                  for part in (entries[:middle], entries[middle:]) if part]
        root["/ParentTree"] = pdf.make_indirect(Dictionary(Kids=Array(leaves)))
    else:
        root["/ParentTree"] = pdf.make_indirect(Dictionary(Nums=Array([v for entry in entries for v in entry])))
    root["/ParentTreeNextKey"] = key
    pdf.Root["/StructTreeRoot"] = root
    pdf.Root["/MarkInfo"] = Dictionary(Marked=True)
    pdf.save(path)
    return path


def _tags(element) -> list[str]:
    return [str(kid.S)[1:] for kid in kids(element) if isinstance(kid, Dictionary) and "/S" in kid]


def _marked_tags(page) -> list[str]:
    return [str(operands[0]) for operands, operator in pikepdf.parse_content_stream(page)
            if str(operator) in ("BMC", "BDC")]


def _owners(pdf, page) -> list:
    key = int(page.obj.StructParents)
    tree = pdf.Root.StructTreeRoot.ParentTree
    leaves = list(tree.Kids) if "/Kids" in tree else [tree]
    for leaf in leaves:
        nums = list(leaf.Nums)
        for index in range(0, len(nums), 2):
            if int(nums[index]) == key:
                return list(nums[index + 1])
    raise AssertionError(f"no parent tree entry for key {key}")


def _tag(path: Path, out: Path):
    with pikepdf.open(path) as pdf:
        result = tag_leftovers(pdf)
        pdf.save(out)
    return result


def test_untagged_paragraph_picture_header_and_page_number_get_their_place(tmp_path):
    source = partly_tagged(tmp_path / "in.pdf")
    result = _tag(source, tmp_path / "out.pdf")

    assert result.pages == 2 and result.elements["P"] == 2 and result.elements["Figure"] == 2
    assert result.artifacts == 6                      # header, thin line and page number on both pages
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        document = pdf.Root.StructTreeRoot.K[0]
        # read right after the tagged paragraph each was drawn after, page by page
        assert _tags(document) == ["H1", "P", "P", "Figure", "H1", "P", "P", "Figure"]
        for page in pdf.pages:
            owners = _owners(pdf, page)
            assert [str(owner.S)[1:] for owner in owners] == ["H1", "P", "P", "Figure"]
            assert all(owner.P.objgen == document.objgen for owner in owners)
            mcids = [int(operands[1].MCID) for operands, operator in pikepdf.parse_content_stream(page)
                     if str(operator) == "BDC" and "/MCID" in operands[1]]
            assert sorted(mcids) == [0, 1, 2, 3]      # new MCIDs, unique on the page
            assert _marked_tags(page).count("/Artifact") == 3
        new_paragraph = kids(document)[2]
        assert list(new_paragraph.K) == [2] and new_paragraph.Pg.objgen == pdf.pages[0].obj.objgen
        assert measure_text_tagging(pdf)["untagged"] == 0

    before = source.read_bytes()
    assert compare_pages(before, str(tmp_path / "out.pdf"), compare_all=True, check_text=True) is None
    assert compare_glyph_positions(before, str(tmp_path / "out.pdf")) is None
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.1-3"] == 0
    assert not {"7.1-1", "7.1-2", "7.4.2-1"} & set(rules)
    assert not [rule for rule in rules if rule.startswith("7.2-") and rule not in ("7.2-34",)]


def test_a_page_without_tags_gets_a_parent_tree_entry_and_is_read_between_its_neighbours(tmp_path):
    source = partly_tagged(tmp_path / "in.pdf", pages=3, untagged_pages=(1,), kids_tree=True)
    result = _tag(source, tmp_path / "out.pdf")

    assert result.pages == 3
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        root = pdf.Root.StructTreeRoot
        middle = pdf.pages[1]
        assert int(middle.obj.StructParents) == 2 and int(root.ParentTreeNextKey) == 3
        assert int(root.ParentTree.Kids[-1].Limits[1]) == 2          # the number tree stays sorted
        document = root.K[0]
        tags = _tags(document)
        # page 1: H1 P + new P Figure; page 2 (untagged): its heading, paragraphs and picture; page 3
        assert tags[:4] == ["H1", "P", "P", "Figure"] and tags[-4:] == ["H1", "P", "P", "Figure"]
        middle_tags = tags[4:-4]
        assert middle_tags[0] == "H1" and "Figure" in middle_tags
        assert all(kid.Pg.objgen == middle.obj.objgen for kid in kids(document)[4:-4])
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.1-3"] == 0 and not {"7.1-1", "7.1-2", "7.4.2-1"} & set(rules)


def test_new_headings_do_not_skip_a_level(tmp_path):
    """An untagged '1.1.1' heading right after a tagged H1 becomes H2, not H3."""
    extra = {0: "BT /F1 15 Tf 72 420 Td (1.1.1 Details of the study) Tj ET "
                "BT /F1 11 Tf 72 400 Td (The details follow in this paragraph, which is long enough.) Tj ET"}
    source = partly_tagged(tmp_path / "in.pdf", pages=2, extra=extra)
    _tag(source, tmp_path / "out.pdf")
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        tags = _tags(pdf.Root.StructTreeRoot.K[0])
        assert "H3" not in tags and tags[:6] == ["H1", "P", "P", "Figure", "H2", "P"]
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.4.2-1"] == 0 and rules["7.1-3"] == 0


def test_content_in_marks_without_mcid_and_unknown_mcids_are_linked(tmp_path):
    """Text inside /Span or /OC marks without an MCID gets an MCID inside the mark; marked
    content whose MCID the parent tree does not know is linked without changing the page."""
    extra = {0: "/Span BMC BT /F1 11 Tf 72 380 Td (A note in a span without an MCID.) Tj ET EMC "
                "/P <</MCID 7>> BDC BT /F1 11 Tf 72 360 Td (Text whose MCID nobody owns.) Tj ET EMC"}
    source = partly_tagged(tmp_path / "in.pdf", pages=2, extra=extra)
    with pikepdf.open(source) as pdf:
        assert Counter(v.rule_id for v in run_verapdf(str(source)))["7.1-3"] > 0
        result = tag_leftovers(pdf)
        pdf.save(tmp_path / "out.pdf")
    assert result.elements["P"] >= 4
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        page = pdf.pages[0]
        owners = _owners(pdf, page)
        assert len(owners) >= 8 and str(owners[7].S) == "/P"          # MCID 7 now has an owner
        operations = [(str(operator), operands) for operands, operator in pikepdf.parse_content_stream(page)]
        span = next(i for i, (name, operands) in enumerate(operations) if name == "BMC" and str(operands[0]) == "/Span")
        assert operations[span + 1][0] == "BT" and operations[span + 2][0] == "Tf"
        assert operations[span + 3][0] == "Td" and operations[span + 4][0] == "BDC"   # the new mark is inside
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.1-3"] == 0 and not {"7.1-1", "7.1-2"} & set(rules)


def test_text_in_a_form_and_elements_outside_the_tree_get_their_place(tmp_path):
    """A form XObject with text and no marks of its own is tagged as one piece; an element that
    owns an MCID but hangs outside the tree is linked in after the content drawn before it."""
    extra = {0: "q 1 0 0 1 72 380 cm /Fm1 Do Q "
                "/P <</MCID 2>> BDC BT /F1 11 Tf 72 340 Td (Owned by an element outside the tree.) Tj ET EMC"}
    source = partly_tagged(tmp_path / "in.pdf", pages=2, extra=extra)
    with pikepdf.open(source) as pdf:
        form = pdf.make_stream(b"BT /F1 11 Tf 0 0 Td (A sentence drawn inside a form XObject.) Tj ET",
                               Type=Name.XObject, Subtype=Name.Form, BBox=[0, -4, 300, 12],
                               Resources=Dictionary(Font=Dictionary(F1=pdf.pages[0].obj.Resources.Font.F1)))
        pdf.pages[0].obj.Resources.XObject["/Fm1"] = form
        page = pdf.pages[0].obj
        orphan = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.P, Pg=page, K=Array([2])))
        pdf.Root.StructTreeRoot.ParentTree.Nums[1].append(orphan)
        pdf.save(tmp_path / "with-form.pdf")
    result = _tag(tmp_path / "with-form.pdf", tmp_path / "out.pdf")
    assert result.linked == 1
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        page = pdf.pages[0]
        operations = [(str(operator), operands) for operands, operator in pikepdf.parse_content_stream(page)]
        do = next(i for i, (name, operands) in enumerate(operations) if name == "Do" and str(operands[0]) == "/Fm1")
        assert operations[do - 1][0] == "BDC" and operations[do + 1][0] == "EMC"
        document = pdf.Root.StructTreeRoot.K[0]
        owners = _owners(pdf, page)
        assert owners[2].P.objgen == document.objgen                  # the outside element is in the tree now
        form_owner = owners[int(operations[do - 1][1][1].MCID)]
        positions = [kid.objgen for kid in kids(document)]
        assert positions.index(form_owner.objgen) < positions.index(owners[2].objgen)
    rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert rules["7.1-3"] == 0 and not {"7.1-1", "7.1-2"} & set(rules)


def test_a_line_is_never_split_into_content_and_decoration(tmp_path, monkeypatch):
    """A footer line drawn letter by letter: if the layout takes some letters for a repeated footer
    (it sees one-letter lines), the whole line stays content, in one paragraph."""
    from pdfaccessguru.tagging import leftovers
    from pdfaccessguru.tagging.layout import Item, Line, analyse

    letters = " ".join(f"({letter}) Tj 6 0 Td" for letter in "Copyright")
    extra = {0: f"BT /F1 9 Tf 72 40 Td {letters} ET"}
    source = partly_tagged(tmp_path / "in.pdf", pages=2, extra=extra)

    def letter_footers(document):
        """As if the layout had seen the first letter as a line of its own that repeats in the footer."""
        pages = analyse(document)
        footer = next(item for item in pages[0] if item.text.startswith("C") and item.rect.y0 > 700)
        line = footer.lines[0]
        split = line.rect.x0 + 5
        letter = Line(fitz.Rect(line.rect.x0, line.rect.y0, split, line.rect.y1), "C", line.size, line.bold)
        rest = Line(fitz.Rect(split + 0.5, line.rect.y0, line.rect.x1, line.rect.y1), line.text[1:], line.size, line.bold)
        pages[0].remove(footer)
        pages[0] += [Item("P", 0, fitz.Rect(rest.rect), [rest], text=rest.text),
                     Item("Artifact", 0, fitz.Rect(letter.rect), [letter], text="C")]
        return pages

    monkeypatch.setattr(leftovers, "analyse", letter_footers)
    _tag(source, tmp_path / "out.pdf")
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        operations = [(str(operator), operands) for operands, operator in pikepdf.parse_content_stream(pdf.pages[0])]
        start = max(i for i, (name, operands) in enumerate(operations) if name == "Td" and float(operands[1]) == 40)
        marks = [str(operands[0]) for name, operands in operations[start:] if name in ("BMC", "BDC")]
        assert marks[0] == "/P" and "/Artifact" not in marks[:-1]          # only the page number after it
        owners = _owners(pdf, pdf.pages[0])
        mcids = [int(operands[1].MCID) for name, operands in operations[start:] if name == "BDC"]
        assert len({owners[mcid].objgen for mcid in mcids}) == 1


def test_tagged_files_without_leftovers_are_left_alone(tmp_path):
    source = partly_tagged(tmp_path / "in.pdf")
    with pikepdf.open(source) as pdf:
        tag_leftovers(pdf)
        pdf.save(tmp_path / "once.pdf")
    with pikepdf.open(tmp_path / "once.pdf") as pdf:
        result = tag_leftovers(pdf)
        assert not result.changed
        assert tag_leftovers(pdf).pages == 0                          # done once per opened file


def test_a_page_with_a_broken_parent_tree_entry_is_left_as_it_was(tmp_path):
    source = partly_tagged(tmp_path / "in.pdf")
    with pikepdf.open(source) as pdf:
        pdf.Root.StructTreeRoot.ParentTree.Nums[1] = Dictionary(Broken=True)
        content = pdf.pages[0].obj.Contents.read_bytes()
        result = tag_leftovers(pdf)
        assert result.skipped["broken parent tree entry"] == 1 and result.pages == 1
        assert pdf.pages[0].obj.Contents.read_bytes() == content


def test_files_without_a_tag_tree_are_left_to_the_full_tagging(tmp_path):
    source = partly_tagged(tmp_path / "in.pdf")
    with pikepdf.open(source) as pdf:
        del pdf.Root["/StructTreeRoot"]
        result = tag_leftovers(pdf)
    assert not result.changed and result.skipped["no usable tag tree"] == 1


def test_the_pipeline_keeps_the_new_tags_and_the_text(tmp_path):
    source = partly_tagged(tmp_path / "in.pdf", pages=3, untagged_pages=(2,))
    before = Counter(v.rule_id for v in run_verapdf(str(source)))
    assert before["7.1-3"] > 0
    report = run_pipeline(str(source), str(tmp_path / "out.pdf"))
    after = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert after["7.1-3"] == 0
    assert all(after[rule] <= before[rule] for rule in after)
    lines = [line["message"] for phase in report["phases"] for run in phase.get("corrections", [])
             for line in run["lines"]]
    assert any("Content that no tag reached was tagged" in line for line in lines)
    assert not any("7.1-3 were undone" in line for phase in report["phases"] for line in
                   [entry["message"] for entry in phase["lines"]])
    with pikepdf.open(tmp_path / "out.pdf") as fixed:
        assert measure_text_tagging(fixed)["untagged"] == 0
    assert compare_pages(source.read_bytes(), str(tmp_path / "out.pdf"), compare_all=True, check_text=True) is None
