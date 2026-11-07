"""
Meaning and structure (Phase 10): problems the automatic PDF/UA check (veraPDF) cannot see,
following the project's taxonomy of semantic violations (Taxonomy_Collection/
semantic_violation_categories.md). The rule is the same as everywhere: change only what can be
changed exactly; list everything else for a person to check.

Changed automatically:
- Picture descriptions that say nothing ("image", "Bild", a file name) are removed before the
  normal fixes run, so the normal step writes a real description (with an AI, or from the caption
  or the text in the picture). "Image of ..." at the start of a description is removed.
- A passage in another language than the document (e.g. a German abstract in an English thesis)
  gets its language, so screen readers switch voice. Only long passages with a clear result.
- Table header cells get their direction (column or row) where the table shows it.

Listed to check (report): link texts like "click here", long picture descriptions, headings
that are paragraphs, documents without headings, bullet lines not tagged as a list, tiny
"pictures" that are probably decoration, and tables without header cells.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pikepdf
from pikepdf import Array, Dictionary, Name

_EMPTY_WORDS = {
    "image", "images", "picture", "pic", "img", "graphic", "graphics", "figure", "fig", "photo", "photograph", "icon",
    "logo", "chart", "diagram", "illustration", "alt", "alt text", "alternative text", "description", "untitled",
    "bild", "bilder", "grafik", "abbildung", "abb", "foto", "symbol", "diagramm", "beschreibung", "unbenannt",
    "image description", "no description", "kein bild", "-", "*", ".",
}
_FILE_NAME = re.compile(r"^[\w\-. ]+\.(png|jpe?g|gif|bmp|tiff?|svg|webp|emf|wmf)$|^(img|dsc|scan|image|bild)[_\- ]?\d+$",
                        re.IGNORECASE)
_PREFIX = re.compile(r"^(an?\s+|the\s+)?(image|picture|photo|photograph|graphic|illustration|screenshot)\s+(of|showing)\s+"
                     r"|^(ein\s+|das\s+)?(bild|foto|grafik|abbildung)\s+(von|des|der|mit|zeigt)\s+", re.IGNORECASE)
_VAGUE_LINKS = {"click here", "here", "more", "read more", "link", "this link", "click", "go", "details", "learn more",
                "hier", "mehr", "weiter", "weiterlesen", "klicken sie hier", "hier klicken", "link", "dieser link"}
_BULLET = re.compile(r"^\s*([•◦▪▫●○■□‣⁃–—\-*·∙⋅\uf0b7\uf0a7\uf0d8\uf0fc]|\(?\d{1,2}[.)]|\(?[a-z][.)])\s+\S")
_LINK_OWNERS = ("P", "H", "H1", "H2", "H3", "H4", "H5", "H6", "LBody", "TD", "TH", "Caption", "Quote",
                "BlockQuote", "Note")
_LONG_DESCRIPTION = 125            # characters (taxonomy: verbose-alt-text)
_LONG_HEADING = 150                # characters
_LANGUAGE_LETTERS = 60             # a passage needs this many letters before its language is set
_TEXT_HOLDERS = ("P", "H", "H1", "H2", "H3", "H4", "H5", "H6", "LBody", "LI", "TD", "TH", "Caption", "Quote",
                 "BlockQuote", "Note", "Lbl")


@dataclass
class MeaningResult:
    alt_cleared: int = 0           # meaningless descriptions removed (written anew by the normal fix)
    alt_prefix: int = 0            # "image of" removed
    language_parts: int = 0        # passages that got their own language
    languages: dict = field(default_factory=dict)          # language -> passages
    table_scope: int = 0           # header cells that got a direction
    vague_links: list = field(default_factory=list)        # (page, text)
    long_alt: list = field(default_factory=list)           # (page, length)
    long_headings: list = field(default_factory=list)      # (page, start of text)
    no_headings: bool = False
    list_like: list = field(default_factory=list)          # (page, start of text)
    tiny_figures: int = 0
    tables_without_headers: int = 0
    links_made: int = 0            # web addresses in the text made clickable
    document_language: tuple = ()  # (was, now) if the document language was corrected

    def as_dict(self) -> dict:
        return {"alt_cleared": self.alt_cleared, "alt_prefix": self.alt_prefix,
                "language_parts": self.language_parts, "languages": self.languages,
                "table_scope": self.table_scope, "vague_links": self.vague_links[:20],
                "vague_links_count": len(self.vague_links), "long_alt": self.long_alt[:20],
                "long_alt_count": len(self.long_alt), "long_headings": self.long_headings[:10],
                "long_headings_count": len(self.long_headings), "no_headings": self.no_headings,
                "list_like": self.list_like[:10], "list_like_count": len(self.list_like),
                "tiny_figures": self.tiny_figures, "tables_without_headers": self.tables_without_headers,
                "links_made": self.links_made, "document_language": list(self.document_language)}


def _norm(text: str) -> str:
    return " ".join(str(text).split()).strip()


def _walk(pdf: pikepdf.Pdf):
    """(element, parent) for every structure element, in reading order."""
    root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(root, Dictionary):
        return
    seen = set()

    def kids(element):
        value = element.get("/K")
        return list(value) if isinstance(value, Array) else [value] if value is not None else []

    stack = [(kid, root) for kid in reversed(kids(root))]
    while stack:
        element, parent = stack.pop()
        if not isinstance(element, Dictionary) or "/S" not in element or element.objgen in seen:
            continue
        seen.add(element.objgen)
        yield element, parent
        stack += [(kid, element) for kid in reversed(kids(element))]


# ------------------------------------------------------------------ before the normal fixes

def clear_empty_descriptions(pdf: pikepdf.Pdf, result: MeaningResult) -> None:
    """Remove picture descriptions that say nothing; remove "image of" from the others."""
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles

    roles = Roles(pdf)
    for element, _ in _walk(pdf):
        if roles.of(element) not in ("Figure", "Formula"):
            continue
        alt = element.get("/Alt")
        if not isinstance(alt, pikepdf.String):
            continue
        text = _norm(alt)
        bare = text.lower().strip(" .:;,")
        if bare in _EMPTY_WORDS or _FILE_NAME.match(text):
            del element["/Alt"]                      # the normal fix writes a real description
            result.alt_cleared += 1
            continue
        shorter = _PREFIX.sub("", text, count=1)
        if shorter != text and len(shorter) >= 3:
            element["/Alt"] = pikepdf.String(shorter[0].upper() + shorter[1:])
            result.alt_prefix += 1


# ------------------------------------------------------------------ after the normal fixes

def check_meaning(pdf: pikepdf.Pdf, result: MeaningResult) -> None:
    from pdfaccessguru.LLM.fallback import detect_language
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles
    from pdfaccessguru.webapp.review import Texts

    roles = Roles(pdf)
    texts = Texts(pdf)
    page_numbers = {page.obj.objgen: number for number, page in enumerate(pdf.pages, start=1)}
    document_language = str(pdf.Root.get("/Lang") or "").split("-")[0].lower()

    def page_of(element) -> int:
        page = element.get("/Pg")
        return page_numbers.get(page.objgen, 0) if isinstance(page, Dictionary) else 0

    elements = list(_walk(pdf))
    passages: list = []                              # (element, language, letters)
    headings = 0
    with_language = set()                           # elements that have, or sit inside, a language
    previous_bullet: tuple | None = None
    for element, parent in elements:
        role = roles.of(element) or ""
        if "/Lang" in element or parent.objgen in with_language:
            with_language.add(element.objgen)
        if role in ("H", "H1", "H2", "H3", "H4", "H5", "H6"):
            headings += 1
            text = _norm(texts.text(element))
            if len(text) > _LONG_HEADING:
                result.long_headings.append((page_of(element), text[:60]))
        elif role in ("Figure", "Formula"):
            alt = element.get("/Alt")
            if isinstance(alt, pikepdf.String) and len(_norm(alt)) > _LONG_DESCRIPTION:
                result.long_alt.append((page_of(element), len(_norm(alt))))
            box = texts.box(element)
            if role == "Figure" and box is not None and (min(box.x1 - box.x0, box.bottom - box.top) < 3
                                                         or max(box.x1 - box.x0, box.bottom - box.top) < 12):
                result.tiny_figures += 1
        elif role == "Link":
            text = _norm(texts.text(element) or _text_under_link(pdf, element, texts)).lower().strip(" .:>»→")
            if text in _VAGUE_LINKS:
                result.vague_links.append((page_of(element), text))
        elif role == "Table":
            _table_headers(element, roles, result)

        # bullet lines that are paragraphs, not a list
        if role == "P" and roles.of(parent) not in ("LI", "LBody", "L"):
            text = _norm(texts.text(element))
            if _BULLET.match(text):
                if previous_bullet is not None and previous_bullet[0] == parent.objgen:
                    if not result.list_like or result.list_like[-1][1] != previous_bullet[2]:
                        result.list_like.append((page_of(element), previous_bullet[2]))
                previous_bullet = (parent.objgen, element, text[:60])
            else:
                previous_bullet = None

        # the language of each longer passage (set below)
        if role in _TEXT_HOLDERS and document_language and element.objgen not in with_language:
            text = _norm(texts.text(element))
            letters = sum(char.isalpha() for char in text)
            if letters >= _LANGUAGE_LETTERS:
                language = detect_language(text, min_confidence=0.97)
                if language:
                    passages.append((element, language.split("-")[0], letters))
                    with_language.add(element.objgen)        # its parts follow it
    result.no_headings = headings == 0 and len(pdf.pages) >= 3
    _set_languages(pdf, passages, document_language, result)
    _link_visible_addresses(pdf, texts, roles, [e for e, _ in elements], result)


def _set_languages(pdf: pikepdf.Pdf, passages: list, document_language: str, result: MeaningResult) -> None:
    """If most of the text is in another language than the document says, the document language
    is corrected (e.g. an English thesis with a German title page and declaration). Then every
    longer passage in another language than the document gets its own language."""
    letters: dict[str, int] = {}
    for _, language, count in passages:
        letters[language] = letters.get(language, 0) + count
    total = sum(letters.values())
    if total and len(passages) >= 5:
        main, share = max(letters.items(), key=lambda item: item[1])
        if main != document_language and share >= 0.6 * total:
            result.document_language = (document_language, main)
            pdf.Root["/Lang"] = pikepdf.String(main)
            document_language = main
    for element, language, _ in passages:
        if language != document_language and "/Lang" not in element:
            element["/Lang"] = pikepdf.String(language)
            result.language_parts += 1
            result.languages[language] = result.languages.get(language, 0) + 1


_URL = re.compile(r"^(https?://[^\s<>\"]{3,}|www\.[^\s<>\"]+\.[a-z]{2,}[^\s<>\"]*)$", re.IGNORECASE)


def _link_visible_addresses(pdf: pikepdf.Pdf, texts, roles, elements: list, result: MeaningResult) -> None:
    """A web address written in the text but not clickable becomes a real link: the address says
    exactly where it goes. It gets a description and a Link tag inside the paragraph it is in."""
    import fitz

    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.links import _WORDS, _language, _short_url

    root = pdf.Root.StructTreeRoot
    tree = root.get("/ParentTree")
    nums = tree.get("/Nums") if isinstance(tree, Dictionary) else None
    if not isinstance(nums, Array) or "/Kids" in tree:
        return                                       # a nested parent tree is left alone
    keys = [int(nums[i]) for i in range(0, len(nums) - 1, 2)]
    next_key = max([int(root.get("/ParentTreeNextKey", 0))] + [k + 1 for k in keys])
    if texts._data is None and len(pdf.pages):
        texts._page(0)                               # makes the snapshot of the file
    words = _WORDS[_language(pdf)]
    # links go into elements that hold text; a list item may only hold its bullet and its body
    # (a Link directly in an LI breaks rule 7.2-20, found on a real thesis)
    holders = [e for e in elements if roles.of(e) in _LINK_OWNERS]
    with fitz.open(stream=texts._data, filetype="pdf") as document:
        for index, page in enumerate(pdf.pages):
            fitz_page = document[index]
            linked = [fitz.Rect(link["from"]) for link in fitz_page.get_links()]
            for x0, y0, x1, y1, word, *_ in fitz_page.get_text("words"):
                address = word.rstrip(".,;:)!?»”\"'")
                rect = fitz.Rect(x0, y0, x1, y1)
                if not _URL.match(address) or any(abs(rect & area) > 0.3 * abs(rect) for area in linked):
                    continue
                center = ((x0 + x1) / 2, (y0 + y1) / 2)
                owners = []
                for element in holders:
                    box = texts.box(element)
                    if box is not None and box.page == index and box.x0 <= center[0] <= box.x1 \
                            and box.top <= center[1] <= box.bottom:
                        owners.append(((box.x1 - box.x0) * (box.bottom - box.top), element))
                if not owners:
                    continue
                owner = min(owners, key=lambda pair: pair[0])[1]
                uri = address if address.lower().startswith("http") else "https://" + address
                area = (rect * ~fitz_page.transformation_matrix).normalize()
                annotation = pdf.make_indirect(Dictionary(
                    Type=Name.Annot, Subtype=Name.Link, Rect=Array([area.x0, area.y0, area.x1, area.y1]),
                    Border=Array([0, 0, 0]), F=4, A=Dictionary(S=Name.URI, URI=pikepdf.String(uri)),
                    Contents=pikepdf.String(f"{words['to'][0].upper()}{words['to'][1:]} {_short_url(uri)}"),
                    StructParent=next_key))
                annotations = page.obj.get("/Annots")
                if not isinstance(annotations, Array):
                    annotations = Array()
                    page.obj["/Annots"] = annotations
                annotations.append(annotation)
                page.obj["/Tabs"] = Name.S
                link = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name.Link, P=owner, Pg=page.obj,
                                                    K=Array([Dictionary(Type=Name.OBJR, Obj=annotation, Pg=page.obj)])))
                kids = owner.get("/K")
                owner["/K"] = Array((list(kids) if isinstance(kids, Array) else [kids] if kids is not None else []) + [link])
                nums.extend([next_key, link])
                next_key += 1
                linked.append(rect)
                result.links_made += 1
    root["/ParentTreeNextKey"] = next_key


def _text_under_link(pdf: pikepdf.Pdf, element, texts) -> str:
    """The visible text of a link whose tag only points to the link area (no text of its own)."""
    import fitz

    value = element.get("/K")
    for kid in (list(value) if isinstance(value, Array) else [value] if value is not None else []):
        if isinstance(kid, Dictionary) and kid.get("/Type") == Name.OBJR:
            annotation, page = kid.get("/Obj"), kid.get("/Pg") or element.get("/Pg")
            rect = annotation.get("/Rect") if isinstance(annotation, Dictionary) else None
            if not isinstance(rect, Array) or len(rect) != 4 or not isinstance(page, Dictionary):
                continue
            index = next((i for i, p in enumerate(pdf.pages) if p.obj.objgen == page.objgen), None)
            if index is None:
                continue
            if texts._data is None:
                texts._page(index)                       # makes the snapshot of the file
            if not hasattr(texts, "_fitz"):
                texts._fitz = fitz.open(stream=texts._data, filetype="pdf")
            fitz_page = texts._fitz[index]
            x0, y0, x1, y1 = (float(v) for v in rect)
            area = (fitz.Rect(x0, y0, x1, y1) * fitz_page.transformation_matrix).normalize()
            return fitz_page.get_textbox(area)
    return ""


def _table_headers(table, roles, result: MeaningResult) -> None:
    """Header cells get a direction: the top row heads columns, the first cell of a row heads that row."""
    rows = []

    def collect(element):
        value = element.get("/K")
        for kid in (list(value) if isinstance(value, Array) else [value] if value is not None else []):
            if isinstance(kid, Dictionary) and "/S" in kid:
                role = roles.of(kid)
                if role == "TR":
                    rows.append([c for c in (list(kid.K) if isinstance(kid.get("/K"), Array) else [kid.get("/K")])
                                 if isinstance(c, Dictionary) and "/S" in c and roles.of(c) in ("TH", "TD")])
                elif role in ("THead", "TBody", "TFoot"):
                    collect(kid)

    collect(table)
    if not rows:
        return
    if not any(roles.of(cell) == "TH" for row in rows for cell in row):
        result.tables_without_headers += 1
        return
    for index, row in enumerate(rows):
        for position, cell in enumerate(row):
            if roles.of(cell) != "TH" or _scope(cell) is not None:
                continue
            if index == 0 and all(roles.of(c) == "TH" for c in row):
                direction = Name.Column
            elif position == 0 and any(roles.of(c) == "TD" for c in row):
                direction = Name.Row
            else:
                continue
            _set_scope(cell, direction)
            result.table_scope += 1


def _attributes(cell) -> list:
    value = cell.get("/A")
    return list(value) if isinstance(value, Array) else [value] if value is not None else []


def _scope(cell):
    for attributes in _attributes(cell):
        if isinstance(attributes, Dictionary) and attributes.get("/O") == Name.Table and "/Scope" in attributes:
            return attributes.Scope
    return None


def _set_scope(cell, direction) -> None:
    for attributes in _attributes(cell):
        if isinstance(attributes, Dictionary) and attributes.get("/O") == Name.Table:
            attributes["/Scope"] = direction
            return
    table_attributes = Dictionary(O=Name.Table, Scope=direction)
    existing = cell.get("/A")
    if existing is None:
        cell["/A"] = table_attributes
    elif isinstance(existing, Array):
        existing.append(table_attributes)
    else:
        cell["/A"] = Array([existing, table_attributes])
