"""
Descriptions of annotations (rule 7.18.1-2: every annotation except form fields and hidden ones
needs /Contents or an /Alt on its tag). Written for all annotations of the document at once,
without an AI:

- links: their visible text and target (see links.py);
- highlights, underlines, strike-outs: the marked text ("Highlighted text: ...");
- comments and text boxes: their own text;
- attached files: the file name; stamps: the stamp's name;
- drawings and media: a short word, listed for checking.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

import pymupdf as fitz
import pikepdf
from pikepdf import Array, Dictionary, Name, Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.links import describe_links

_WORDS = {
    "en": {"Highlight": "Highlighted text", "Underline": "Underlined text", "StrikeOut": "Crossed-out text",
           "Squiggly": "Underlined text", "FileAttachment": "Attached file", "Stamp": "Stamp",
           "comment": "Comment", "drawing": "Drawing", "media": "Media", "annotation": "Annotation"},
    "de": {"Highlight": "Hervorgehobener Text", "Underline": "Unterstrichener Text",
           "StrikeOut": "Durchgestrichener Text", "Squiggly": "Unterstrichener Text",
           "FileAttachment": "Angehängte Datei", "Stamp": "Stempel", "comment": "Kommentar",
           "drawing": "Zeichnung", "media": "Medien", "annotation": "Anmerkung"},
}
_DRAWINGS = ("/Square", "/Circle", "/Line", "/Polygon", "/PolyLine", "/Ink", "/Caret")
_MEDIA = ("/Sound", "/Movie", "/Screen", "/3D", "/RichMedia")
_SKIPPED = ("/Widget", "/Popup", "/PrinterMark", "/TrapNet", "/Link")
_HIDDEN = 2


@dataclass
class AnnotationResult:
    described: int = 0
    generic: int = 0
    links: int = 0


def _plain(rich_text) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", str(rich_text)).split())


def _marked_text(page: fitz.Page, annotation: Dictionary) -> str:
    points = annotation.get("/QuadPoints")
    areas = []
    if isinstance(points, Array) and len(points) >= 8:
        values = [float(v) for v in points]
        for i in range(0, len(values) - 7, 8):
            xs, ys = values[i:i + 8:2], values[i + 1:i + 8:2]
            areas.append(fitz.Rect(min(xs), min(ys), max(xs), max(ys)))
    elif isinstance(annotation.get("/Rect"), Array):
        x0, y0, x1, y1 = (float(v) for v in annotation.Rect)
        areas.append(fitz.Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
    parts = [" ".join(page.get_textbox(area * page.transformation_matrix).split()) for area in areas]
    text = " ".join(part for part in parts if part)
    return text if len(text) <= 200 else text[:200].rsplit(" ", 1)[0] + " ..."


def _has_alt_on_tag(pdf: Pdf, annotation: Dictionary) -> bool:
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import _parent_tree_slot
    key = annotation.get("/StructParent")
    slot = _parent_tree_slot(pdf, int(key)) if key is not None else None
    owner = slot[0][slot[1]] if slot else None
    return isinstance(owner, Dictionary) and bool(str(owner.get("/Alt", "")).strip())


def describe_annotations(pdf: Pdf) -> AnnotationResult:
    result = AnnotationResult()
    words = _WORDS["de" if str(pdf.Root.get("/Lang", "")).lower().startswith("de") else "en"]
    buffer = io.BytesIO()
    pdf.save(buffer)                    # one copy for reading text, shared with the links
    with fitz.open(stream=buffer.getvalue(), filetype="pdf") as document:
        links = describe_links(pdf, document=document)
        result.links = links.described
        result.generic += links.generic
        for index, page in enumerate(pdf.pages):
            annotations = page.obj.get("/Annots")
            if not isinstance(annotations, Array):
                continue
            for annotation in annotations:
                if not isinstance(annotation, Dictionary):
                    continue
                kind = str(annotation.get("/Subtype", ""))
                if kind in _SKIPPED or int(annotation.get("/F", 0)) & _HIDDEN:
                    continue
                if str(annotation.get("/Contents", "")).strip() or _has_alt_on_tag(pdf, annotation):
                    continue
                text, generic = "", False
                if kind in ("/Highlight", "/Underline", "/StrikeOut", "/Squiggly"):
                    marked = _marked_text(document[index], annotation)
                    text = f"{words[kind[1:]]}: {marked}" if marked else words[kind[1:]]
                elif kind in ("/Text", "/FreeText"):
                    text = _plain(annotation.get("/RC", "")) or words["comment"]
                    generic = text == words["comment"]
                elif kind == "/FileAttachment":
                    spec = annotation.get("/FS")
                    name = (spec.get("/UF") or spec.get("/F")) if isinstance(spec, Dictionary) else None
                    text = f"{words['FileAttachment']}: {name}" if name else words["FileAttachment"]
                elif kind == "/Stamp":
                    name = str(annotation.get("/Name", "")).lstrip("/")
                    text = f"{words['Stamp']}: {name}" if name else words["Stamp"]
                elif kind in _DRAWINGS:
                    text, generic = words["drawing"], True
                elif kind in _MEDIA:
                    text, generic = words["media"], True
                else:
                    text, generic = words["annotation"], True
                annotation["/Contents"] = pikepdf.String(text)
                result.described += 1
                result.generic += generic
    return result
