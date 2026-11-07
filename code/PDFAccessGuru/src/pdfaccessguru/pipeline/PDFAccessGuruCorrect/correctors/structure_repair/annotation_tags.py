"""
Annotations in the tag tree (rule 7.18.1-1: an annotation other than a form field, link or
printer's mark must be nested in an Annot tag).

Each such annotation gets an Annot tag that points to it. The tag is placed right after the tag
of the text the annotation covers, so a screen reader meets the comment where it belongs;
without such text, after the last content of its page. The first version retagged the
surrounding element and wrote a description taken from page 1.
"""

from __future__ import annotations

from dataclasses import dataclass

from pikepdf import Array, Dictionary, Name, Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.layout import Layout
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import (
    Roles, _parent_tree_slot, index_of, is_element, kids, move, new_element, set_kids,
)
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.link_annotation_artifact_not_nested_tag_link import (
    _insert_number_tree_entry, _next_parent_tree_key,
)

_NOT_ANNOT = (Name.Widget, Name.Link, Name.PrinterMark, Name.Popup)


@dataclass
class AnnotationTagResult:
    tagged: int = 0
    placed_by_text: int = 0


def _owner(pdf: Pdf, annotation: Dictionary):
    key = annotation.get("/StructParent")
    slot = _parent_tree_slot(pdf, int(key)) if key is not None else None
    owner = slot[0][slot[1]] if slot else None
    return owner if is_element(owner) else None


def _anchor(pdf: Pdf, layout: Layout, page_index: int, annotation: Dictionary):
    """The tag of the text under the annotation, else of the last content on the page."""
    page = pdf.pages[page_index].obj
    parsed = layout._page(page_index)
    key = page.get("/StructParents")
    slot = _parent_tree_slot(pdf, int(key)) if key is not None else None
    owners = slot[0][slot[1]] if slot else None
    if parsed is None or not isinstance(owners, Array) or not parsed.boxes:
        return None, False
    height = float(page.MediaBox[3]) - float(page.MediaBox[1])
    x0, y0, x1, y1 = (float(v) for v in annotation.get("/Rect", [0, 0, 0, 0]))
    left, right = min(x0, x1), max(x0, x1)
    top, bottom = height - max(y0, y1), height - min(y0, y1)

    def owner_of(mcid):
        element = owners[mcid] if 0 <= mcid < len(owners) else None
        return element if is_element(element) else None

    covered = [mcid for mcid, box in parsed.boxes.items()
               if box.x0 <= right and box.x1 >= left and box.top <= bottom and box.bottom >= top]
    for mcid in sorted(covered):
        element = owner_of(mcid)
        if element is not None:
            return element, True
    for mcid in sorted(parsed.boxes, reverse=True):
        element = owner_of(mcid)
        if element is not None:
            return element, False
    return None, False


def tag_annotations(pdf: Pdf) -> AnnotationTagResult:
    result = AnnotationTagResult()
    root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(root, Dictionary):
        return result
    roles = Roles(pdf)
    layout = Layout(pdf)
    if not isinstance(root.get("/ParentTree"), Dictionary):
        root["/ParentTree"] = pdf.make_indirect(Dictionary(Nums=Array()))
    for page_index, page in enumerate(pdf.pages):
        annotations = page.obj.get("/Annots")
        if not isinstance(annotations, Array):
            continue
        for annotation in annotations:
            if not isinstance(annotation, Dictionary) or annotation.get("/Subtype") in _NOT_ANNOT:
                continue
            owner = _owner(pdf, annotation)
            if owner is not None and roles.is_(owner, "Annot"):
                continue
            if owner is not None:
                # already referenced from another tag: wrap the reference in an Annot tag in place
                parts = kids(owner)
                position = next((i for i, part in enumerate(parts) if isinstance(part, Dictionary)
                                 and part.get("/Type") == Name.OBJR and part.get("/Obj") is not None
                                 and part.Obj.objgen == annotation.objgen), None)
                if position is None:
                    continue
                tag = new_element(pdf, "Annot", owner, like=owner)
                set_kids(tag, move(pdf, [parts[position]], owner, tag))
                parts[position] = tag
                set_kids(owner, parts)
                result.tagged += 1
                continue
            anchor, by_text = _anchor(pdf, layout, page_index, annotation)
            parent = anchor.get("/P") if anchor is not None else None
            if not is_element(parent):
                document = next((kid for kid in kids(root) if is_element(kid)), None)
                parent, anchor = (document, None) if document is not None else (root, None)
            tag = new_element(pdf, "Annot", parent)
            tag["/Pg"] = page.obj
            reference = Dictionary(Type=Name.OBJR, Obj=annotation, Pg=page.obj)
            set_kids(tag, [reference])
            siblings = kids(parent)
            position = index_of(siblings, anchor) if anchor is not None else None
            siblings.insert(len(siblings) if position is None else position + 1, tag)
            set_kids(parent, siblings)
            key = _next_parent_tree_key(root, root.ParentTree)
            _insert_number_tree_entry(root.ParentTree, key, tag)
            annotation["/StructParent"] = key
            root["/ParentTreeNextKey"] = key + 1
            result.tagged += 1
            result.placed_by_text += by_text
    return result
