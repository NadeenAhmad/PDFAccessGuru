"""
Descriptions of links (rule 7.18.5-2: a link annotation needs /Contents).

The description is the link's visible text plus where it goes, e.g.
"Annual report 2023 (link to example.com/report)" or "Link to page 5". It is written for all
links of the document at once; an AI is asked only for links without visible text whose target
cannot be read (if an AI is set up).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

import pymupdf as fitz
import pikepdf
from pikepdf import Array, Dictionary, Name, Pdf

_WORDS = {
    "en": {"link": "Link", "to": "link to", "page": "page", "email": "email to", "file": "file"},
    "de": {"link": "Link", "to": "Link zu", "page": "Seite", "email": "E-Mail an", "file": "Datei"},
}


@dataclass
class LinkResult:
    described: int = 0
    by_ai: int = 0
    generic: int = 0


def _language(pdf: Pdf) -> str:
    return "de" if str(pdf.Root.get("/Lang", "")).lower().startswith("de") else "en"


def _short_url(uri: str) -> str:
    uri = unquote(uri.strip())
    parsed = urlparse(uri)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    text = host + (path if len(path) <= 40 else path[:37] + "...")
    return text or uri[:60]


def _page_number(pdf: Pdf, destination) -> int | None:
    if isinstance(destination, (pikepdf.String, Name)):
        names = pdf.Root.get("/Names")
        tree = names.get("/Dests") if isinstance(names, Dictionary) else None
        target = None
        if tree is not None:
            try:
                target = pikepdf.NameTree(tree).get(str(destination).lstrip("/"))
            except Exception:
                target = None
        if target is None and isinstance(pdf.Root.get("/Dests"), Dictionary):
            target = pdf.Root.Dests.get("/" + str(destination).lstrip("/"))
        destination = target.get("/D") if isinstance(target, Dictionary) else target
    if isinstance(destination, Array) and len(destination) and isinstance(destination[0], Dictionary):
        for index, page in enumerate(pdf.pages):
            if page.obj.objgen == destination[0].objgen:
                return index + 1
    return None


def describe_target(pdf: Pdf, annotation: Dictionary, words: dict) -> str | None:
    """Where a link goes, in a few words ("example.com/report", "page 5"), or None."""
    action = annotation.get("/A")
    if isinstance(action, Dictionary):
        kind = action.get("/S")
        if kind == Name.URI and action.get("/URI") is not None:
            uri = str(action.URI)
            if uri.lower().startswith("mailto:"):
                return f"{words['email']} {uri[7:].split('?')[0]}"
            return _short_url(uri)
        if kind == Name.GoTo:
            page = _page_number(pdf, action.get("/D"))
            return f"{words['page']} {page}" if page else None
        if kind in (Name.GoToR, Name.Launch):
            target = action.get("/F")
            name = target.get("/F") if isinstance(target, Dictionary) else target
            return f"{words['file']} {str(name).split('/')[-1]}" if name is not None else None
    if annotation.get("/Dest") is not None:
        page = _page_number(pdf, annotation.Dest)
        return f"{words['page']} {page}" if page else None
    return None


def _visible_text(page: fitz.Page, annotation: Dictionary) -> str:
    rect = annotation.get("/Rect")
    if not isinstance(rect, Array) or len(rect) != 4:
        return ""
    x0, y0, x1, y1 = (float(v) for v in rect)
    area = fitz.Rect(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)) * page.transformation_matrix
    text = " ".join(page.get_textbox(area).split())
    return text[:150]


def _target_key(annotation: Dictionary) -> str | None:
    action = annotation.get("/A")
    if isinstance(action, Dictionary) and action.get("/S") == Name.URI and action.get("/URI") is not None:
        return "uri:" + str(action.URI)
    if isinstance(action, Dictionary) and action.get("/S") == Name.GoTo and action.get("/D") is not None:
        return "goto:" + repr(action.D)
    if annotation.get("/Dest") is not None:
        return "goto:" + repr(annotation.Dest)
    return None


def _rect(annotation: Dictionary) -> tuple | None:
    rect = annotation.get("/Rect")
    if not isinstance(rect, Array) or len(rect) != 4:
        return None
    x0, y0, x1, y1 = (float(v) for v in rect)
    return min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)


def _joined_texts(page: fitz.Page, annotations: list) -> dict:
    """One link split into pieces (one per word or per line, as some programs write them) gets the
    text of all its pieces: neighbouring links to the same place, on the same or the next line."""
    joined: dict = {}
    group: list = []

    def close() -> None:
        if len(group) > 1:
            text = " ".join(_visible_text(page, a) for a in group).strip()
            for annotation in group:
                joined[annotation.objgen] = text[:150]

    for annotation in annotations:
        key, rect = _target_key(annotation), _rect(annotation)
        if group and key is not None and rect is not None and _target_key(group[-1]) == key:
            previous = _rect(group[-1])
            height = max(previous[3] - previous[1], 1)
            same_line = min(rect[3], previous[3]) - max(rect[1], previous[1]) > 0.5 * height \
                and rect[0] - previous[2] < 20
            next_line = 0 <= previous[1] - rect[3] < 1.5 * height and rect[0] < previous[2]
            if same_line or next_line:
                group.append(annotation)
                continue
        close()
        group = [annotation] if key is not None and rect is not None else []
    close()
    return joined


def describe_links(pdf: Pdf, ask_ai=None, document: fitz.Document | None = None) -> LinkResult:
    """
    Give every link without a description one. ask_ai(annotation, page_number) -> str | None may
    write a text for links that have neither visible text nor a readable target.
    """
    if document is None:
        buffer = io.BytesIO()
        pdf.save(buffer)
        with fitz.open(stream=buffer.getvalue(), filetype="pdf") as opened:
            return describe_links(pdf, ask_ai, opened)
    result = LinkResult()
    words = _WORDS[_language(pdf)]
    for index, page in enumerate(pdf.pages):
        annotations = page.obj.get("/Annots")
        if not isinstance(annotations, Array):
            continue
        links = [a for a in annotations if isinstance(a, Dictionary) and a.get("/Subtype") == Name.Link]
        joined = _joined_texts(document[index], links)
        for annotation in links:
            if str(annotation.get("/Contents", "")).strip():
                continue
            visible = joined.get(annotation.objgen) or _visible_text(document[index], annotation)
            target = describe_target(pdf, annotation, words)
            is_email = bool(target) and target.startswith(words["email"])
            if len(re.sub(r"\W", "", visible)) >= 2:
                core = target.split()[-1] if target else ""
                shown = not target or core.lower() in visible.lower() or _short_url(visible) == target
                text = visible if shown else f"{visible} ({target if is_email else words['to'] + ' ' + target})"
            elif target:
                phrase = target if is_email else f"{words['to']} {target}"
                text = phrase[0].upper() + phrase[1:]
            else:
                text = ask_ai(annotation, index + 1) if ask_ai else None
                if text:
                    result.by_ai += 1
                else:
                    text = words["link"]
                    result.generic += 1
            annotation["/Contents"] = pikepdf.String(text)
            result.described += 1
    return result
