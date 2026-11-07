"""
"What a screen reader reads" (Phase 7b): the tag tree of the fixed PDF shown as a simple web
page, in reading order: headings, paragraphs, lists, tables, and pictures by their description.
Decoration is left out, just like a screen reader leaves it out. Sighted people can use it to
check the reading order and the headings without a screen reader.
"""

from __future__ import annotations

import html
from pathlib import Path

import pikepdf
from pikepdf import Dictionary

MAX_PAGES = 30

_GROUPING = {"Document", "Part", "Art", "Sect", "Div", "NonStruct", "Private", "BlockQuote", "TOC", "Index",
             "THead", "TBody", "TFoot", "Ruby", "Warichu"}

TEXT = {
    "en": {"title": "Title", "language": "Language", "none": "(none)", "picture": "Picture", "formula": "Formula",
           "no_description": "no description", "page": "Page {n}", "more": "Only the first {n} pages are shown.",
           "untagged": "This file has no tags, so assistive technologies present it as one long text without structure.",
           "link": "link"},
    "de": {"title": "Titel", "language": "Sprache", "none": "(keiner)", "picture": "Bild", "formula": "Formel",
           "no_description": "keine Beschreibung", "page": "Seite {n}", "more": "Es werden nur die ersten {n} Seiten gezeigt.",
           "untagged": "Diese Datei hat keine Tags. Assistive Technologien geben sie deshalb als einen langen Text ohne Gliederung wieder.",
           "link": "Link"},
}


def preview_html(fixed: Path, ui_language: str = "en", max_pages: int = MAX_PAGES) -> str:
    from pdfaccessguru.webapp.review import Texts, _kids, _role, document_title

    t = TEXT.get(ui_language, TEXT["en"])
    with pikepdf.open(fixed) as pdf:
        language = str(pdf.Root.get("/Lang") or "")
        title = document_title(pdf)
        out = [f"<p><strong>{t['title']}:</strong> {html.escape(title) or t['none']}<br>"
               f"<strong>{t['language']}:</strong> {html.escape(language) or t['none']}</p>"]
        root = pdf.Root.get("/StructTreeRoot")
        if not isinstance(root, Dictionary):
            return "\n".join(out + [f"<p>{t['untagged']}</p>"])
        layout = Texts(pdf)
        page_numbers = {page.obj.objgen: number for number, page in enumerate(pdf.pages, start=1)}
        state = {"page": 0, "stopped": False}
        seen: set = set()

        def page_of(element) -> int:
            page = element.get("/Pg")
            return page_numbers.get(page.objgen, 0) if isinstance(page, Dictionary) else 0

        def marker(element) -> None:
            number = page_of(element)
            if number > max_pages:
                state["stopped"] = True
            elif number > state["page"]:
                state["page"] = number
                out.append(f'<p class="page-marker">{html.escape(t["page"].format(n=number))}</p>')

        def text_of(element) -> str:
            text = html.escape(" ".join(layout.text(element).split()))
            return f'<span lang="{html.escape(language)}">{text}</span>' if text and language else text

        def described(element, word: str) -> str:
            alt = element.get("/Alt")
            description = str(alt).strip() if isinstance(alt, pikepdf.String) else ""
            if description:
                return f"<p>[{word}: {html.escape(description)}]</p>"
            return f'<p class="missing">[{word}: {t["no_description"]}]</p>'

        def walk(element, depth: int = 0) -> None:
            if state["stopped"] or not isinstance(element, Dictionary) or "/S" not in element or depth > 60:
                return
            if element.objgen in seen:
                return
            seen.add(element.objgen)
            role = _role(pdf, element)
            marker(element)
            if state["stopped"]:
                return
            children = [kid for kid in _kids(element) if isinstance(kid, Dictionary) and "/S" in kid]
            if role in _GROUPING:
                for kid in children:
                    walk(kid, depth + 1)
            elif role in ("H1", "H2", "H3", "H4", "H5", "H6", "H"):
                level = min(6, int(role[1]) + 1) if role != "H" else 3
                out.append(f"<h{level}>{text_of(element)}</h{level}>")
            elif role == "Figure":
                out.append(described(element, t["picture"]))
            elif role == "Formula":
                out.append(described(element, t["formula"]))
            elif role in ("L", "TOC"):
                out.append("<ul>")
                for kid in children:
                    walk(kid, depth + 1)
                out.append("</ul>")
            elif role in ("LI", "TOCI"):
                out.append(f"<li>{text_of(element)}</li>")
            elif role == "Table":
                out.append("<table>")
                for kid in children:
                    walk(kid, depth + 1)
                out.append("</table>")
            elif role == "TR":
                cells = []
                for kid in children:
                    kind = "th" if _role(pdf, kid) == "TH" else "td"
                    cells.append(f"<{kind}>{text_of(kid)}</{kind}>")
                out.append("<tr>" + "".join(cells) + "</tr>")
            elif role == "Link":
                contents = text_of(element) or _link_description(element)
                out.append(f"<p>{contents} ({t['link']})</p>" if contents else f"<p>({t['link']})</p>")
            else:                                          # paragraphs, captions, notes, ...
                text = text_of(element)
                if text:
                    out.append(f"<p>{text}</p>")
                for kid in children:                       # pictures inside a paragraph
                    if _role(pdf, kid) in ("Figure", "Formula"):
                        walk(kid, depth + 1)

        for kid in _kids(root):
            walk(kid)
        if state["stopped"]:
            out.append(f"<p>{html.escape(t['more'].format(n=max_pages))}</p>")
    return '<div class="preview">' + "\n".join(out) + "</div>"


def _link_description(element) -> str:
    """What a screen reader says for a link without text of its own: its description."""
    alt = element.get("/Alt")
    if isinstance(alt, pikepdf.String) and str(alt).strip():
        return html.escape(str(alt).strip())
    for kid in (element.get("/K") if isinstance(element.get("/K"), pikepdf.Array) else [element.get("/K")]):
        if isinstance(kid, Dictionary) and kid.get("/Type") == "/OBJR":
            contents = kid.get("/Obj", Dictionary()).get("/Contents")
            if isinstance(contents, pikepdf.String) and str(contents).strip():
                return html.escape(str(contents).strip())
    return ""
