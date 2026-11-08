"""
Building the tag tree of an untagged PDF (Phase 6): one Document element with headings,
paragraphs, lists, figures, captions and tables in reading order, links inside their paragraph; every MCID is registered in the
parent tree, so screen readers find the owner of each piece of content.
"""

from __future__ import annotations

import io
from collections import Counter
from dataclasses import dataclass, field

import pymupdf as fitz
import pikepdf
from pikepdf import Array, Dictionary, Name

from pdfaccessguru.tagging.layout import analyse
from pdfaccessguru.tagging.marking import mark_page


@dataclass
class TagResult:
    pages: int = 0
    elements: Counter = field(default_factory=Counter)
    replaced_share: float | None = None       # share of text the replaced old tags covered


# A tag tree that covers less than this share of the text is replaced by automatic tagging.
NEARLY_EMPTY = 0.05


def _without_mcids(owner) -> list | None:
    """The content of a page or form without its MCID marks (None if it has none)."""
    out, keep, removed = [], [], False
    for operands, operator in pikepdf.parse_content_stream(owner):
        name = str(operator)
        if name in ("BMC", "BDC"):
            props = operands[1] if len(operands) > 1 else None
            tagged = isinstance(props, Dictionary) and props.get("/MCID") is not None
            keep.append(not tagged)
            if tagged:
                removed = True
                continue
        elif name == "EMC":
            if keep and not keep.pop():
                continue
        out.append((operands, operator))
    return out if removed else None


def _strip_forms(pdf: pikepdf.Pdf, resources, seen: set) -> None:
    """MCID marks inside form XObjects too, at every depth (old tags there would end up inside
    decoration once the page is tagged anew: rule 7.1-2)."""
    xobjects = resources.get("/XObject") if isinstance(resources, Dictionary) else None
    for xobject in (xobjects.values() if isinstance(xobjects, Dictionary) else []):
        if not isinstance(xobject, pikepdf.Stream) or xobject.get("/Subtype") != Name.Form or xobject.objgen in seen:
            continue
        seen.add(xobject.objgen)
        try:
            cleaned = _without_mcids(xobject)
        except Exception:
            cleaned = None
        if cleaned is not None:
            xobject.write(pikepdf.unparse_content_stream(cleaned))
        if "/StructParents" in xobject:
            del xobject["/StructParents"]
        _strip_forms(pdf, xobject.get("/Resources"), seen)


def strip_tags(pdf: pikepdf.Pdf) -> None:
    """Remove a tag tree and the MCID marks in the page content and its form XObjects
    (decoration and other marks stay)."""
    seen: set = set()
    for page in pdf.pages:
        cleaned = _without_mcids(page)
        if cleaned is not None:
            page.obj["/Contents"] = pdf.make_stream(pikepdf.unparse_content_stream(cleaned))
        _strip_forms(pdf, page.obj.get("/Resources"), seen)
        if "/StructParents" in page.obj:
            del page.obj["/StructParents"]
        for annotation in page.obj.get("/Annots") or []:
            if isinstance(annotation, Dictionary) and "/StructParent" in annotation:
                del annotation["/StructParent"]
    del pdf.Root["/StructTreeRoot"]


def _tag_links(pdf: pikepdf.Pdf, page: pikepdf.Page, fitz_page: fitz.Page, items, elements: dict[int, Dictionary],
               document: Dictionary, children: list, nums: list, next_key: int) -> int:
    """
    Every link gets a Link tag inside the tag of the text it is on (so a screen reader meets it
    in the sentence), pointing to the link annotation. Returns the next free parent tree key.
    """
    for annotation in page.obj.get("/Annots") or []:
        if not isinstance(annotation, Dictionary) or annotation.get("/Subtype") != Name.Link:
            continue
        rect = annotation.get("/Rect")
        if not isinstance(rect, Array) or len(rect) != 4:
            continue
        x0, y0, x1, y1 = (float(v) for v in rect)
        middle = fitz.Point((x0 + x1) / 2, (y0 + y1) / 2) * fitz_page.transformation_matrix
        owner_index = next((i for i, item in enumerate(items) if i in elements and item.contains(middle, margin=4)), None)
        parent = elements[owner_index] if owner_index is not None else document
        link = _element(pdf, "Link", parent, page.obj)
        link["/K"] = Array([Dictionary(Type=Name.OBJR, Obj=annotation, Pg=page.obj)])
        if owner_index is None:
            children.append(link)
        else:
            kids = parent.get("/K")
            parent["/K"] = Array((list(kids) if isinstance(kids, Array) else [kids] if kids is not None else []) + [link])
        annotation["/StructParent"] = next_key
        nums.append((next_key, link))
        next_key += 1
    return next_key


def _element(pdf: pikepdf.Pdf, tag: str, parent: Dictionary, page: Dictionary, mcids: list[int] | None = None) -> Dictionary:
    element = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name("/" + tag), P=parent, Pg=page))
    if mcids is not None:
        element["/K"] = Array(mcids)
    return element


def tag_document(pdf: pikepdf.Pdf) -> TagResult:
    """
    Tag a PDF that has no tags. A PDF whose tags cover almost none of its text (less than 5%,
    e.g. only a title page tagged by a template) is tagged anew; otherwise nothing is done.
    """
    result = TagResult()
    existing = pdf.Root.get("/StructTreeRoot")
    if isinstance(existing, Dictionary) and existing.get("/K") is not None:
        from pdfaccessguru.pipeline.text_tagging import measure_text_tagging
        share = measure_text_tagging(pdf).get("tagged_share", 1.0)
        if share >= NEARLY_EMPTY:
            return result
        strip_tags(pdf)
        result.replaced_share = share
    buffer = io.BytesIO()
    pdf.save(buffer)
    with fitz.open(stream=buffer.getvalue(), filetype="pdf") as layout_document:
        pages = analyse(layout_document)
        root = pdf.make_indirect(Dictionary(Type=Name.StructTreeRoot))
        document = _element(pdf, "Document", root, pdf.pages[0].obj if len(pdf.pages) else Dictionary())
        children: list[Dictionary] = []
        nums: list[tuple[int, object]] = []          # parent tree entries, sorted at the end
        next_key = len(pdf.pages)                   # parent tree keys of annotations come after the pages
        for index, page in enumerate(pdf.pages):
            items = pages[index]
            marks = mark_page(pdf, page, layout_document[index], items)
            owners: dict[int, Dictionary] = {}
            elements: dict[int, Dictionary] = {}
            current_list: Dictionary | None = None
            table_element, row_element, row_number = None, None, None
            for item_index, item in enumerate(items):
                mcids = marks.mcids.get(item_index)
                if item.kind == "Table":
                    current_list = None
                    table_element = _element(pdf, "Table", document, page.obj)
                    table_element["/K"] = Array()
                    children.append(table_element)
                    row_element, row_number = None, None
                    result.elements["Table"] += 1
                    continue
                if item.kind == "Cell" and table_element is not None:
                    if row_number != item.row:                 # every row of the grid, also empty ones
                        row_element = _element(pdf, "TR", table_element, page.obj)
                        row_element["/K"] = Array()
                        table_element.K.append(row_element)
                        row_number = item.row
                    cell = _element(pdf, "TH" if item.header else "TD", row_element, page.obj, mcids or [])
                    attributes = Dictionary(O=Name.Table)
                    if item.header:
                        attributes["/Scope"] = Name.Column
                    if item.col_span > 1:
                        attributes["/ColSpan"] = item.col_span
                    if item.row_span > 1:
                        attributes["/RowSpan"] = item.row_span
                    if len(attributes) > 1:
                        cell["/A"] = attributes
                    row_element.K.append(cell)
                    elements[item_index] = cell
                    for mcid in mcids or []:
                        owners[mcid] = cell
                    result.elements["TH" if item.header else "TD"] += 1
                    continue
                if not mcids:
                    current_list = None if item.kind != "Artifact" else current_list
                    continue
                if item.kind == "LI":
                    if current_list is None:
                        current_list = _element(pdf, "L", document, page.obj)
                        current_list["/K"] = Array()
                        children.append(current_list)
                        result.elements["L"] += 1
                    list_item = _element(pdf, "LI", current_list, page.obj)
                    body = _element(pdf, "LBody", list_item, page.obj, mcids)
                    list_item["/K"] = Array([body])
                    current_list.K.append(list_item)
                    owner = body
                    elements[item_index] = body
                    result.elements["LI"] += 1
                else:
                    current_list = None
                    tag = f"H{item.level}" if item.kind == "H" else item.kind
                    owner = _element(pdf, tag, document, page.obj, mcids)
                    children.append(owner)
                    elements[item_index] = owner
                    result.elements[tag] += 1
                for mcid in mcids:
                    owners[mcid] = owner
            size = max(owners) + 1 if owners else 0
            nums.append((index, Array([owners.get(mcid) for mcid in range(size)])))
            page.obj["/StructParents"] = index
            page.obj["/Tabs"] = Name.S
            before = next_key
            next_key = _tag_links(pdf, page, layout_document[index], items, elements, document, children, nums, next_key)
            result.elements["Link"] += next_key - before
        document["/K"] = Array(children)
        root["/K"] = Array([document])
        flat = Array([value for key, entry in sorted(nums, key=lambda pair: pair[0]) for value in (key, entry)])
        root["/ParentTree"] = pdf.make_indirect(Dictionary(Nums=flat))
        root["/ParentTreeNextKey"] = next_key
        pdf.Root["/StructTreeRoot"] = root
        mark_info = pdf.Root.get("/MarkInfo")
        if not isinstance(mark_info, Dictionary):
            mark_info = Dictionary()
            pdf.Root["/MarkInfo"] = mark_info
        mark_info["/Marked"] = True
        result.pages = len(pdf.pages)
    return result
