"""
Checking and editing the texts the tool wrote (Phase 7b): document title and language, picture
and formula descriptions, link descriptions and form field descriptions. Everything is read from
the fixed PDF itself, and edits are written back into it, so the page always shows what a screen
reader will read.

A text counts as written by the tool if the original file did not contain it. Title and
language are always shown, because every reader meets them first.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf as fitz
import pikepdf
from pikepdf import Array, Dictionary, Name

GROUPS = ("document", "pictures", "formulas", "links", "fields")
_LANGUAGE_TAG = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*$")
_MAX_CONTEXT = 200


@dataclass
class Entry:
    key: str                  # what to change: "title", "lang", or "<object>-<generation>-<field>"
    group: str                # one of GROUPS
    text: str
    page: int | None = None   # 1-based
    context: str = ""         # caption, nearby text, link target or field name, to compare with
    has_picture: bool = False


def version(path: Path) -> str:
    """Changes whenever the file changes: edits are only applied to the version they were made on."""
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]


def _strings_in(pdf: pikepdf.Pdf) -> set[str]:
    """Every Alt, Contents and TU text in a file (to tell texts the tool wrote from existing ones)."""
    found = set()
    for obj in pdf.objects:
        if isinstance(obj, Dictionary):
            for field in ("/Alt", "/Contents", "/TU"):
                value = obj.get(field)
                if isinstance(value, pikepdf.String):
                    found.add(str(value).strip())
    return found


def _key(obj, field: str) -> str:
    number, generation = obj.objgen
    return f"{number}-{generation}-{field}"


def _kids(element) -> list:
    kids = element.get("/K")
    return list(kids) if isinstance(kids, Array) else [kids] if kids is not None else []


def _elements(pdf: pikepdf.Pdf):
    """(element, parent, index in parent) for every structure element, in reading order."""
    root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(root, Dictionary):
        return
    stack = [(kid, root, index) for index, kid in reversed(list(enumerate(_kids(root))))]
    seen = set()
    while stack:
        element, parent, index = stack.pop()
        if not isinstance(element, Dictionary) or "/S" not in element or element.objgen in seen:
            continue
        seen.add(element.objgen)
        yield element, parent, index
        stack += [(kid, element, i) for i, kid in reversed(list(enumerate(_kids(element))))]


def _role(pdf: pikepdf.Pdf, element) -> str:
    role = str(element.get("/S"))
    role_map = pdf.Root.StructTreeRoot.get("/RoleMap")
    for _ in range(5):                                   # custom names map to standard ones
        if isinstance(role_map, Dictionary) and role in role_map:
            role = str(role_map[role])
        else:
            break
    return role.lstrip("/")


class Texts:
    """
    Text and position of structure elements. pdfplumber gives single letters; many PDFs have no
    space characters but only gaps, so a space is put where the gap between two letters is wide
    or a new line starts.
    """

    def __init__(self, pdf: pikepdf.Pdf):
        from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.layout import Layout

        self.pdf = pdf
        self.layout = Layout(pdf)

    @property
    def _data(self) -> bytes | None:
        return self.layout._snapshot

    def _page(self, index: int):
        return self.layout._page(index)

    def text(self, element) -> str:
        return self.layout.text(element, spaced=True)

    def box(self, element):
        return self.layout.box(element)


def document_title(pdf: pikepdf.Pdf) -> str:
    try:            # read only: as a "with" block, pikepdf would write the metadata back and sync it
        title = str(pdf.open_metadata().get("dc:title") or "")
    except Exception:
        title = ""
    return title or str(pdf.docinfo.get("/Title") or "")


def collect(fixed: Path, original: Path) -> list[Entry]:
    with pikepdf.open(original) as source:
        existing = _strings_in(source)
    entries: list[Entry] = []
    with pikepdf.open(fixed) as pdf:
        entries.append(Entry("title", "document", document_title(pdf)))
        entries.append(Entry("lang", "document", str(pdf.Root.get("/Lang") or "")))
        page_numbers = {page.obj.objgen: number for number, page in enumerate(pdf.pages, start=1)}
        layout = Texts(pdf)
        for element, parent, index in _elements(pdf):
            role = _role(pdf, element)
            if role not in ("Figure", "Formula"):
                continue
            alt = element.get("/Alt")
            text = str(alt).strip() if isinstance(alt, pikepdf.String) else ""
            if text in existing and text:
                continue
            page = element.get("/Pg")
            box = layout.box(element)
            entries.append(Entry(_key(element, "Alt"), "pictures" if role == "Figure" else "formulas", text,
                                 page=box.page + 1 if box else page_numbers.get(page.objgen) if isinstance(page, Dictionary) else None,
                                 context=_nearby_text(pdf, layout, parent, index), has_picture=box is not None))
        with fitz.open(fixed) as document:
            for number, page in enumerate(pdf.pages, start=1):
                for annotation in page.obj.get("/Annots") or []:
                    if not isinstance(annotation, Dictionary):
                        continue
                    subtype = annotation.get("/Subtype")
                    field = "/Contents" if subtype == Name.Link else "/TU" if subtype == Name.Widget else None
                    if field is None:
                        continue
                    target = annotation if field == "/Contents" or "/T" in annotation else annotation.get("/Parent", annotation)
                    value = target.get(field)
                    text = str(value).strip() if isinstance(value, pikepdf.String) else ""
                    if text in existing and text:
                        continue
                    entries.append(Entry(_key(target, field.lstrip("/")), "links" if field == "/Contents" else "fields",
                                         text, page=number, context=_annotation_context(document, number, annotation, target)))
    return entries


def _nearby_text(pdf, layout, parent, index) -> str:
    """The caption of a picture, or else the text just before or after it."""
    siblings = _kids(parent)
    for offset in (1, -1, 2, -2):
        position = index + offset
        if 0 <= position < len(siblings) and isinstance(siblings[position], Dictionary) and "/S" in siblings[position]:
            text = layout.text(siblings[position])
            if text:
                label = "Caption" if _role(pdf, siblings[position]) == "Caption" else "Nearby text"
                return f"{label}: {text[:_MAX_CONTEXT]}"
    return ""


def _annotation_context(document, number: int, annotation, target) -> str:
    if annotation.get("/Subtype") == Name.Widget:
        name = target.get("/T")
        return f"Field name: {name}" if name is not None else ""
    parts = []
    rect = annotation.get("/Rect")
    if isinstance(rect, Array) and len(rect) == 4:
        page = document[number - 1]
        x0, y0, x1, y1 = (float(v) for v in rect)
        area = fitz.Rect(x0, y0, x1, y1) * page.transformation_matrix
        visible = " ".join(page.get_textbox(area.normalize()).split())
        if visible:
            parts.append(f"Text on the page: {visible[:_MAX_CONTEXT].rstrip(' .')}")
    action = annotation.get("/A")
    if isinstance(action, Dictionary) and action.get("/URI") is not None:
        parts.append(f"Goes to: {str(action.URI)[:_MAX_CONTEXT]}")
    elif annotation.get("/Dest") is not None or (isinstance(action, Dictionary) and action.get("/S") == Name.GoTo):
        parts.append("Goes to: a place in this document")
    return ". ".join(parts)


def picture(fixed: Path, key: str) -> bytes | None:
    """A picture of the area a figure or formula covers (for sighted readers), as PNG."""
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.layout import Layout

    number, generation, _ = key.split("-", 2)
    with pikepdf.open(fixed) as pdf:
        try:
            element = pdf.get_object((int(number), int(generation)))
        except Exception:
            return None
        box = Layout(pdf).box(element) if isinstance(element, Dictionary) else None
    if box is None:
        return None
    with fitz.open(fixed) as document:
        page = document[box.page]
        clip = fitz.Rect(box.x0, box.top, box.x1, box.bottom) & page.rect
        if clip.is_empty:
            return None
        zoom = min(2.0, 500 / max(clip.width, clip.height, 1))
        return page.get_pixmap(clip=clip, matrix=fitz.Matrix(zoom, zoom)).tobytes("png")


class EditError(ValueError):
    pass


def apply(fixed: Path, changes: dict[str, str], show: dict[str, str] | None = None) -> int:
    """
    Write changed texts into the PDF, and show pictures that were hidden as decoration (key ->
    description). Returns how many things changed. Empty texts and invalid language tags are
    refused (EditError), because they would make the file worse. Everything is saved at once:
    saving renumbers the objects the keys refer to.
    """
    changed = 0
    with pikepdf.open(fixed) as pdf:
        for key, description in (show or {}).items():
            changed += _unhide(pdf, key, description)
        for key, text in changes.items():
            text = " ".join(text.split())
            if not text:
                raise EditError("empty")
            if key == "title":
                if document_title(pdf) != text:
                    pdf.docinfo["/Title"] = text
                    with pdf.open_metadata(set_pikepdf_as_editor=False) as metadata:
                        metadata["dc:title"] = text
                    changed += 1
                continue
            if key == "lang":
                if not _LANGUAGE_TAG.match(text):
                    raise EditError("language")
                if str(pdf.Root.get("/Lang") or "") != text:
                    pdf.Root["/Lang"] = pikepdf.String(text)
                    changed += 1
                continue
            number, generation, field = key.split("-", 2)
            if field not in ("Alt", "Contents", "TU"):
                continue
            obj = pdf.get_object((int(number), int(generation)))
            if not isinstance(obj, Dictionary):
                continue
            if str(obj.get("/" + field) or "") != text:
                obj["/" + field] = pikepdf.String(text)
                changed += 1
        if changed:
            temporary = fixed.with_name(fixed.name + ".saving")
            pdf.save(temporary)
    if changed:
        os.replace(temporary, fixed)
    return changed


# ---------------------------------------------------------------- what was hidden as decoration

MIN_PICTURE = 16          # points; smaller drawings (bullets, rules) are not listed


@dataclass
class HiddenPicture:
    key: str                  # "img-<object>-<generation>" of the picture
    pages: list[int]          # 1-based pages where it is hidden
    first: tuple[int, tuple[float, float, float, float]]   # page index and box (PDF coordinates)


def _matrix(a, b) -> list[float]:
    return [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2],
            a[2] * b[1] + a[3] * b[3], a[4] * b[0] + a[5] * b[2] + b[4], a[4] * b[1] + a[5] * b[3] + b[5]]


def _hidden_draws(pdf: pikepdf.Pdf, page: pikepdf.Page):
    """(operator index, picture object, box) for every picture drawn inside decoration on a page."""
    xobjects = (page.obj.get("/Resources") or Dictionary()).get("/XObject") or Dictionary()
    ctm, stack, marks = [1.0, 0, 0, 1.0, 0, 0], [], []
    for index, (operands, operator) in enumerate(pikepdf.parse_content_stream(page)):
        name = str(operator)
        if name == "q":
            stack.append(list(ctm))
        elif name == "Q" and stack:
            ctm = stack.pop()
        elif name == "cm" and len(operands) == 6:
            ctm = _matrix([float(v) for v in operands], ctm)
        elif name in ("BMC", "BDC"):
            marks.append(str(operands[0]) if operands else "")
        elif name == "EMC" and marks:
            marks.pop()
        elif name == "Do" and "/Artifact" in marks:
            xobject = xobjects.get(str(operands[0]))
            if isinstance(xobject, pikepdf.Stream) and xobject.get("/Subtype") == Name.Image:
                corners = [(x * ctm[0] + y * ctm[2] + ctm[4], x * ctm[1] + y * ctm[3] + ctm[5])
                           for x, y in ((0, 0), (1, 0), (0, 1), (1, 1))]
                xs, ys = [c[0] for c in corners], [c[1] for c in corners]
                yield index, xobject, (min(xs), min(ys), max(xs), max(ys))


def hidden_pictures(fixed: Path) -> list[HiddenPicture]:
    """Pictures the file shows only as decoration (one entry per picture, with the pages it is on)."""
    found: dict[str, HiddenPicture] = {}
    with pikepdf.open(fixed) as pdf:
        for page_index, page in enumerate(pdf.pages):
            try:
                draws = list(_hidden_draws(pdf, page))
            except Exception:
                continue
            for _, xobject, box in draws:
                if box[2] - box[0] < MIN_PICTURE or box[3] - box[1] < MIN_PICTURE:
                    continue
                key = "img-{}-{}".format(*xobject.objgen)
                entry = found.setdefault(key, HiddenPicture(key, [], (page_index, box)))
                if page_index + 1 not in entry.pages:
                    entry.pages.append(page_index + 1)
    return list(found.values())


def hidden_text(fixed: Path, limit: int = 12) -> list[tuple[str, int]]:
    """Lines of text shown only as decoration (page headers, footers, page numbers), with how many
    pages each is on (numbers are ignored when counting, so "Page 1" and "Page 2" count together)."""
    import pdfplumber

    lines: dict[str, tuple[str, set]] = {}
    try:
        with pdfplumber.open(fixed) as document:
            for page in document.pages:
                rows: dict[int, list] = {}
                for char in page.chars:
                    if char.get("tag") == "Artifact":
                        rows.setdefault(round(char["top"] / 3), []).append(char)
                for chars in rows.values():
                    chars.sort(key=lambda c: c["x0"])
                    text, previous = "", None
                    for char in chars:
                        if previous is not None and char["x0"] - previous["x1"] > max(char["size"], 1) * 0.15:
                            text += " "
                        text += char["text"]
                        previous = char
                    text = " ".join(text.split())
                    if sum(c.isalnum() for c in text) < 1:
                        continue
                    key = re.sub(r"\d+", "#", text)
                    shown, pages = lines.setdefault(key, (text, set()))
                    pages.add(page.page_number)
    except Exception:
        return []
    return [(text, len(pages)) for text, pages in list(lines.values())[:limit]]


def hidden_picture_png(fixed: Path, key: str) -> bytes | None:
    for entry in hidden_pictures(fixed):
        if entry.key == key:
            page_index, (x0, y0, x1, y1) = entry.first
            with fitz.open(fixed) as document:
                page = document[page_index]
                clip = (fitz.Rect(x0, y0, x1, y1) * page.transformation_matrix) & page.rect
                if clip.is_empty:
                    return None
                zoom = min(2.0, 500 / max(clip.width, clip.height, 1))
                return page.get_pixmap(clip=clip, matrix=fitz.Matrix(zoom, zoom)).tobytes("png")
    return None


def _parent_tree_array(root, key: int):
    """The parent tree entry (array of owners by MCID) of a page, in a flat or one-level tree."""
    tree = root.get("/ParentTree")
    for node in [tree] + list((tree.get("/Kids") or []) if isinstance(tree, Dictionary) else []):
        nums = node.get("/Nums") if isinstance(node, Dictionary) else None
        if isinstance(nums, Array):
            for i in range(0, len(nums) - 1, 2):
                if int(nums[i]) == key:
                    return nums, i + 1
    return None, None


_CONTAINERS = ("L", "LI", "LBody", "Lbl", "Table", "TR", "TH", "TD", "THead", "TBody", "TFoot", "TOC", "TOCI", "Span", "Link")


def _unhide(pdf: pikepdf.Pdf, key: str, description: str) -> int:
    """
    Show a picture that was hidden as decoration to assistive technologies: every place it is drawn
    as decoration becomes a Figure with the given description, placed in the reading order after
    the text above it. Returns how many places changed. Raises EditError if the file's tag tree
    cannot take it.
    """
    description = " ".join(description.split())
    if not description:
        raise EditError("empty_picture")
    changed = 0
    root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(root, Dictionary):
        raise EditError("structure")
    texts = Texts(pdf)
    elements = [(element, parent) for element, parent, _ in _elements(pdf)]
    for page_index, page in enumerate(pdf.pages):
        draws = [(index, box) for index, xobject, box in _hidden_draws(pdf, page)
                 if "img-{}-{}".format(*xobject.objgen) == key]
        if not draws:
            continue
        operations = list(pikepdf.parse_content_stream(page))
        used = [int(o[1]["/MCID"]) for o, op in operations
                if str(op) == "BDC" and len(o) > 1 and isinstance(o[1], Dictionary) and "/MCID" in o[1]]
        mcid = max(used, default=-1) + 1
        if "/StructParents" not in page.obj:
            next_key = int(root.get("/ParentTreeNextKey", len(pdf.pages)))
            page.obj["/StructParents"] = next_key
            root["/ParentTreeNextKey"] = next_key + 1
            tree = root.get("/ParentTree")
            if not isinstance(tree, Dictionary):
                tree = pdf.make_indirect(Dictionary(Nums=Array()))
                root["/ParentTree"] = tree
            if isinstance(tree.get("/Nums"), Array):
                tree.Nums.extend([next_key, Array()])
        nums, slot = _parent_tree_array(root, int(page.obj.StructParents))
        if nums is None:
            raise EditError("structure")
        owners = nums[slot]
        if not isinstance(owners, Array):
            owners = Array([owners]) if owners is not None else Array()
            nums[slot] = owners
        page_height = float(page.obj.MediaBox[3])
        replacements: dict[int, list] = {}
        for index, box in draws:
            figure = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.Figure, Pg=page.obj, K=mcid,
                                                  Alt=pikepdf.String(description)))
            # in reading order: after the last element on this page that starts above the picture
            top = page_height - box[3]
            anchor = None
            for element, parent in elements:
                found = texts.box(element)
                if found is not None and found.page == page_index and found.top <= top:
                    anchor = (element, parent)
            while anchor is not None and str(anchor[0].get("/S")).lstrip("/") in _CONTAINERS:
                anchor = _climb(anchor, elements)
            if anchor is None:
                parent = root.K[0] if isinstance(root.get("/K"), Array) and len(root.K) and "/S" in root.K[0] else root
                kids = parent.get("/K")
                parent["/K"] = Array([figure] + (list(kids) if isinstance(kids, Array) else [kids] if kids is not None else []))
            else:
                element, parent = anchor
                kids = list(parent.K) if isinstance(parent.get("/K"), Array) else [parent.get("/K")]
                position = next(i for i, kid in enumerate(kids) if isinstance(kid, Dictionary) and kid.objgen == element.objgen)
                parent["/K"] = Array(kids[:position + 1] + [figure] + kids[position + 1:])
            figure["/P"] = parent
            while len(owners) <= mcid:
                owners.append(None)
            owners[mcid] = figure
            replacements[index] = [([Name.Figure, Dictionary(MCID=mcid)], pikepdf.Operator("BDC"))]
            mcid += 1
            changed += 1
        # the picture leaves its decoration block: close it before, open a Figure, reopen after
        out = []
        for index, (operands, operator) in enumerate(operations):
            if index in replacements:
                out.append(([], pikepdf.Operator("EMC")))
                out += replacements[index]
                out.append((operands, operator))
                out.append(([], pikepdf.Operator("EMC")))
                out.append(([Name.Artifact], pikepdf.Operator("BMC")))
            else:
                out.append((operands, operator))
        page.obj["/Contents"] = pdf.make_stream(pikepdf.unparse_content_stream(out))
    return changed


def _climb(anchor, elements):
    """From an element inside a list, table or link, up to the block that holds it."""
    element, parent = anchor
    for e, p in elements:
        if e.objgen == parent.objgen:
            return (e, p)
    return None
