"""Phase 4b: annotation descriptions, annotations in the tag tree, and protected PDFs."""

from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

import pikepdf
import pytest
from pikepdf import Array, Dictionary, Name

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.annotations import describe_annotations
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.annotation_tags import tag_annotations
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import kids, parent_tree_owner
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.pipeline.pipeline import run_pipeline

RESOURCES = Path(__file__).resolve().parents[1] / "resources"


def _tagged_page_with_annotations():
    """One paragraph 'Important result' at (72, 700) and three annotations on it."""
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(612, 792))
    page = pdf.pages[0].obj
    font = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica))
    page["/Resources"] = Dictionary(Font=Dictionary(F1=font))
    page["/Contents"] = pdf.make_stream(b"/P <</MCID 0>> BDC BT /F1 12 Tf 72 700 Td (Important result) Tj ET EMC")
    page["/StructParents"] = 0
    root = pdf.make_indirect(Dictionary(Type=Name.StructTreeRoot))
    document = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.Document, P=root))
    paragraph = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.P, P=document, Pg=page, K=0))
    closing = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.P, P=document, Pg=page))
    document["/K"] = Array([paragraph, closing])
    root["/K"] = Array([document])
    root["/ParentTree"] = pdf.make_indirect(Dictionary(Nums=Array([0, Array([paragraph])])))
    root["/ParentTreeNextKey"] = 1
    pdf.Root["/StructTreeRoot"] = root
    highlight = Dictionary(Type=Name.Annot, Subtype=Name.Highlight, Rect=[70, 695, 170, 712],
                           QuadPoints=[70, 712, 170, 712, 70, 695, 170, 695])
    note = Dictionary(Type=Name.Annot, Subtype=Name.Text, Rect=[180, 700, 200, 720],
                      RC=pikepdf.String("<body><p>Check this number</p></body>"))
    attachment = Dictionary(Type=Name.Annot, Subtype=Name.FileAttachment, Rect=[300, 300, 310, 310],
                            FS=Dictionary(Type=Name.Filespec, F=pikepdf.String("data.xlsx")))
    page["/Annots"] = Array([pdf.make_indirect(highlight), pdf.make_indirect(note), pdf.make_indirect(attachment)])
    return pdf, document, paragraph


def test_annotations_get_plain_descriptions_without_ai():
    pdf, _, _ = _tagged_page_with_annotations()
    result = describe_annotations(pdf)
    texts = [str(annotation.Contents) for annotation in pdf.pages[0].obj.Annots]
    assert texts == ["Highlighted text: Important result", "Check this number", "Attached file: data.xlsx"]
    assert result.described == 3 and result.generic == 0


def test_annotations_are_tagged_next_to_the_text_they_mark():
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import _parent_tree_slot

    pdf, document, paragraph = _tagged_page_with_annotations()
    result = tag_annotations(pdf)
    assert result.tagged == 3 and result.placed_by_text == 1      # only the highlight lies on the text
    order = [str(kid.S) for kid in kids(document)]
    assert order == ["/P", "/Annot", "/Annot", "/Annot", "/P"]   # right after the paragraph, before the next one
    for annotation in pdf.pages[0].obj.Annots:
        nums, index = _parent_tree_slot(pdf, int(annotation.StructParent))
        tag = nums[index]
        assert str(tag.S) == "/Annot" and kids(tag)[0].Obj.objgen == annotation.objgen


def test_pipeline_tags_annotations_of_the_verapdf_test_file(tmp_path):
    source = tmp_path / "a.pdf"
    shutil.copy(RESOURCES / "veraPDF_corpus/7.18.1-t01-fail-a.pdf", source)
    assert "7.18.1-1" in {v.rule_id for v in run_verapdf(str(source))}
    run_pipeline(str(source), str(tmp_path / "out.pdf"))
    assert "7.18.1-1" not in {v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf"))}


@pytest.fixture
def locked_pdf(tmp_path) -> Path:
    """A protected PDF (protection level R3) that does not let screen readers read it."""
    path = tmp_path / "locked.pdf"
    with pikepdf.open(RESOURCES / "veraPDF_corpus/7.5-t01-fail-a.pdf") as pdf:
        pdf.save(path, encryption=pikepdf.Encryption(owner="secret", user="", R=3, aes=False, metadata=False,
                                                     allow=pikepdf.Permissions(accessibility=False, extract=False)))
    assert "7.16-1" in {v.rule_id for v in run_verapdf(str(path))}
    return path


def test_protected_pdf_without_owner_password_is_left_as_it_is(locked_pdf, tmp_path):
    run_pipeline(str(locked_pdf), str(tmp_path / "out.pdf"))
    assert "7.16-1" in {v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf"))}


def test_owner_password_lets_screen_readers_in_and_keeps_everything_else(locked_pdf, tmp_path):
    run_pipeline(str(locked_pdf), str(tmp_path / "out.pdf"), owner_password="secret")
    assert "7.16-1" not in {v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf"))}
    with pikepdf.open(tmp_path / "out.pdf") as out:
        assert out.is_encrypted and out.encryption.R == 3
        assert out.allow.accessibility and not out.allow.extract
    with pikepdf.open(tmp_path / "out.pdf", password="secret"):
        pass                                                      # the owner password still works
