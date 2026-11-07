"""
The report as a PDF (Phase 7b): drawn from the same accessible HTML as the browser app, so every
script works (MuPDF lays out Arabic, Hebrew, Chinese, Hindi, ... with its built-in fonts), and
then tagged with PDFAccessGuru's own tagger: headings, paragraphs, lists, tables, and pictures
with their descriptions. The language, the title and the PDF/UA marks are set, so the report is
itself readable with a screen reader.
"""

from __future__ import annotations

import io
import re

import fitz
import pikepdf

_IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)\)\s*$", re.MULTILINE)

_CSS = """
body { font-family: sans-serif; font-size: 11pt; line-height: 1.35; }
h1 { font-size: 17pt; margin: 0 0 8pt 0; }
h2 { font-size: 14pt; margin: 14pt 0 6pt 0; }
h3 { font-size: 12pt; margin: 10pt 0 4pt 0; }
p, ul { margin: 0 0 6pt 0; }
ul, ul ul, li { list-style-type: disc !important; }   /* the circle of nested lists has no text value */
table { border-collapse: collapse; margin: 4pt 0 8pt 0; }
th, td { border: 0.6pt solid black; padding: 3pt; text-align: start; vertical-align: top; }
img { max-width: 100%; max-height: 220pt; }
"""


def render_report_pdf(markdown: str, title: str, images: dict[str, bytes] | None = None,
                      language: str = "en") -> bytes:
    """
    Render a report as a tagged PDF. Markdown image lines (![...](path)) are drawn from
    `images` (path -> PNG bytes); lines whose image is missing are left out.
    """
    from pdfaccessguru.reporting.report_language import text_direction
    from pdfaccessguru.webapp.markdown_html import markdown_to_html

    images = images or {}
    markdown = _IMAGE.sub(lambda match: match.group(0) if match.group(2) in images else "", markdown)
    descriptions = [match.group(1) for match in _IMAGE.finditer(markdown)]
    archive = fitz.Archive()
    for path, data in images.items():
        archive.add(data, path)
    html_body = markdown_to_html(markdown)
    css = _CSS
    if text_direction(language) == "rtl":
        # MuPDF puts list bullets on the left even in right-to-left text; a bullet character at
        # the start of each item lands on the right, where readers expect it
        html_body = html_body.replace("<li>", "<li>• ")
        css += "\nul, ul ul, li { list-style-type: none !important; padding: 0; margin: 0; }"
    body, texts = _number_blocks(html_body)
    page_html = f'<body lang="{language}" dir="{text_direction(language)}">{body}</body>'
    story = fitz.Story(html=page_html, user_css=css, archive=archive)

    buffer = io.BytesIO()
    writer = fitz.DocumentWriter(buffer)
    mediabox = fitz.paper_rect("a4")
    where = mediabox + (54, 54, -54, -54)
    places: dict[str, list[tuple[int, fitz.Rect]]] = {}

    def remember(position) -> None:
        if position.id in texts and position.open_close & 1:
            places.setdefault(position.id, []).append((position.page_num, fitz.Rect(position.rect)))

    more, page_number = True, 0
    while more:
        device = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.element_positions(remember, {"page_num": page_number})
        story.draw(device)
        writer.end_page()
        page_number += 1
    writer.close()
    blocks = [(texts[key], places[key]) for key in texts if key in places]
    return _make_accessible(buffer.getvalue(), title, language, descriptions,
                            blocks if language.split("-")[0] in JOINED_SCRIPTS else None)


# Languages whose letters change shape and join (or are reordered) when drawn. MuPDF draws
# them correctly but does not record the letters behind every joined shape, so screen readers
# would read some of them wrongly. For these, every tagged paragraph, heading, list item and
# table cell gets its exact text as /ActualText, which screen readers read instead.
JOINED_SCRIPTS = {"ar", "fa", "ur", "ps", "sd", "ug", "ckb", "he", "yi", "dv", "hi", "mr", "ne", "sa", "bn", "as",
                  "pa", "gu", "or", "ta", "te", "kn", "ml", "si", "th", "lo", "km", "my", "bo", "dz"}
_BLOCK_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "th", "td")


def _number_blocks(body: str) -> tuple[str, dict[str, str]]:
    """Give every paragraph, heading, list item and table cell an id; return the plain text of each."""
    from html.parser import HTMLParser

    texts: dict[str, str] = {}
    stack: list[str] = []
    counter = iter(range(1_000_000))

    class Numberer(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.out: list[str] = []

        def handle_starttag(self, tag, attrs):
            text = self.get_starttag_text()
            if tag in _BLOCK_TAGS and not stack:
                key = f"b{next(counter)}"
                stack.append(key)
                texts[key] = ""
                text = text[:-1] + f' id="{key}">' if not text.endswith("/>") else text
            elif stack:
                stack.append("")
            self.out.append(text)

        def handle_endtag(self, tag):
            if stack:
                stack.pop()
            self.out.append(f"</{tag}>")

        def handle_startendtag(self, tag, attrs):
            self.out.append(self.get_starttag_text())

        def handle_data(self, data):
            for key in stack[:1]:
                texts[key] += data
            import html as html_module
            self.out.append(html_module.escape(data, quote=False))

    parser = Numberer()
    parser.feed(body)
    parser.close()
    return "".join(parser.out), {key: " ".join(text.split()) for key, text in texts.items()}


def _set_actual_text(pdf: pikepdf.Pdf, blocks: list[tuple[str, list[tuple[int, fitz.Rect]]]]) -> None:
    """Each tagged text element gets the exact text of the HTML blocks it covers (in order)."""
    from pdfaccessguru.webapp.review import Texts

    texts = Texts(pdf)
    used: set[int] = set()
    for element in _elements(pdf):
        if str(element.get("/S")).lstrip("/") not in ("P", "H1", "H2", "H3", "H4", "H5", "H6", "LBody", "LI", "TH", "TD",
                                                      "Caption"):
            continue
        if any(isinstance(kid, pikepdf.Dictionary) and "/S" in kid for kid in _kids(element)):
            continue                                          # only elements that hold the text themselves
        box = texts.box(element)
        if box is None:
            continue
        area = fitz.Rect(box.x0, box.top, box.x1, box.bottom)
        covered = []
        for index, (text, places) in enumerate(blocks):
            for page, rect in places:
                # a block belongs to the element if most of its height lies within the element's lines
                # and they share some width (blocks are as wide as the page, text is often shorter)
                vertical = min(rect.y1, area.y1) - max(rect.y0, area.y0)
                horizontal = min(rect.x1, area.x1) - max(rect.x0, area.x0)
                if page == box.page and horizontal > 0 and vertical >= 0.5 * max(min(rect.height, area.height), 1):
                    covered.append(index)
                    break
        if not covered:
            continue
        new = [index for index in covered if index not in used]
        used.update(new)
        element["/ActualText"] = pikepdf.String(" ".join(blocks[index][0] for index in new))


def _kids(element) -> list:
    kids = element.get("/K")
    return list(kids) if isinstance(kids, pikepdf.Array) else [kids] if kids is not None else []


def _make_accessible(data: bytes, title: str, language: str, descriptions: list[str], blocks=None) -> bytes:
    from pdfaccessguru.tagging.builder import tag_document

    with pikepdf.open(io.BytesIO(data)) as pdf:
        tag_document(pdf)
        figures = [element for element in _elements(pdf) if element.get("/S") == "/Figure"]
        for figure, description in zip(figures, descriptions):
            figure["/Alt"] = pikepdf.String(description)
        if blocks:
            _set_actual_text(pdf, blocks)
        pdf.Root["/Lang"] = pikepdf.String(language)
        pdf.Root["/ViewerPreferences"] = pikepdf.Dictionary(DisplayDocTitle=True)
        with pdf.open_metadata(set_pikepdf_as_editor=False) as metadata:
            metadata["dc:title"] = title
            metadata["dc:language"] = [language]
            metadata.register_xml_namespace("http://www.aiim.org/pdfua/ns/id/", "pdfuaid")
            metadata["pdfuaid:part"] = "1"
        pdf.docinfo["/Title"] = title
        output = io.BytesIO()
        pdf.save(output)
        return output.getvalue()


def _elements(pdf: pikepdf.Pdf):
    """All structure elements in reading order."""
    found = []

    def walk(element) -> None:
        kids = element.get("/K")
        for kid in list(kids) if isinstance(kids, pikepdf.Array) else [kids] if kids is not None else []:
            if isinstance(kid, pikepdf.Dictionary) and "/S" in kid:
                found.append(kid)
                walk(kid)

    walk(pdf.Root.StructTreeRoot)
    return found
