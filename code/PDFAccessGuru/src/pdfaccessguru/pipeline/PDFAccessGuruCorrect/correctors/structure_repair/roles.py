"""
Custom tag names (rules 7.1-5 and 7.1-6).

Programs like Word, LibreOffice and InDesign name tags after their styles ("Footnote",
"Überschrift 2", "TextBox"). Each custom name must lead to a standard tag through the role map.
The first version mapped every custom name to a paragraph, so headings, notes and links lost
their meaning. Here each name is mapped by what it says, and only names that say nothing are
mapped by what the tags contain (a container becomes a neutral group, text a paragraph).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from pikepdf import Dictionary, Name, Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import STANDARD_TYPES, is_element, kids
from pdfaccessguru.pipeline.reporting.writer import report_info, report_review

_BY_LOWER = {name.lower(): name for name in STANDARD_TYPES}

# Words in custom names and the standard tag they stand for, checked in this order.
_WORDS: list[tuple[str, str]] = [
    (r"^(toc|tableofcontents|inhaltsverzeichnis|contents)$", "TOC"),
    (r"^(toc|contents|inhalt|verzeichnis)\s*\d+$|^toci$|tocentry|tocitem", "TOCI"),
    (r"foot\s*note|end\s*note|fußnote|fussnote|^note$|anmerkung", "Note"),
    (r"^(goto|gotor|uri|link|hyperlink|internet link|internetlink)$", "Link"),
    (r"caption|beschriftung|legende", "Caption"),
    (r"^(title|titel)$", "H1"),
    (r"list\s*item|^li$|listenpunkt", "LI"),
    (r"list\s*body|^lbody$", "LBody"),
    (r"^(label|lbl|bullet\s*label)$", "Lbl"),
    (r"^(list|liste|bullets?|num\s*list|aufzählung)$", "L"),
    (r"table\s*head|^th$", "TH"),
    (r"^(table|tabelle)$", "Table"),
    (r"^(row|table\s*row|zeile)$", "TR"),
    (r"^(cell|table\s*cell|zelle)$", "TD"),
    (r"inline\s*shape|figure|image|picture|graphic|grafik|bild|abbildung|photo|chart|diagram|shape|logo", "Figure"),
    (r"formula|equation|formel", "Formula"),
    (r"block\s*quote|zitat|quotation", "BlockQuote"),
    (r"^code$|preformatted|source\s*code", "Code"),
    (r"^(section|sect|chapter|kapitel|slide|worksheet)$", "Sect"),
    (r"^(article|art)$", "Art"),
    (r"^(part|teil)$", "Part"),
    (r"text\s*box|textbox|frame|rahmen|group|container|box|cover|artifact", "Div"),
    (r"underline|emphasis|strong|bold|italic|superscript|subscript|char|inline|span", "Span"),
    (r"paragraph|para|body|text|normal|standard|absatz|fliesstext|textkörper|plain|spacing|index|contents", "P"),
]
_HEADING = re.compile(r"(heading|überschrift|titre|titulo|header)\s*(\d)$|^h(\d)$", re.IGNORECASE)


@dataclass
class RoleMapResult:
    mapped: dict[str, str] = field(default_factory=dict)      # custom name -> standard tag
    guessed: list[str] = field(default_factory=list)          # names mapped by content only
    removed: list[str] = field(default_factory=list)          # standard tags mapped in a circle


def guess_by_name(name: str) -> str | None:
    """The standard tag a custom name stands for, or None if the name says nothing."""
    clean = name.strip()
    if clean.lower() in _BY_LOWER:                                 # "Lbody" -> "LBody"
        return _BY_LOWER[clean.lower()]
    heading = _HEADING.search(clean)
    if heading:
        level = int(heading.group(2) or heading.group(3))
        return f"H{min(max(level, 1), 6)}"
    lower = clean.lower()
    for pattern, tag in _WORDS:
        if re.search(pattern, lower):
            return tag
    return None


def _guess_by_content(elements: list[Dictionary]) -> str:
    """A neutral tag from what the elements with this name contain."""
    has_children = any(is_element(kid) for element in elements for kid in kids(element))
    if has_children:
        return "Div"
    inline_parents = sum(1 for element in elements
                         if str(element.get("/P", {}).get("/S", "")) in ("/P", "/Span", "/Link", "/H1", "/H2", "/H3",
                                                                          "/H4", "/H5", "/H6", "/H", "/LBody", "/Lbl"))
    return "Span" if inline_parents > len(elements) / 2 else "P"


def _resolves(name: str, role_map: Dictionary | None) -> bool:
    seen = set()
    while name not in STANDARD_TYPES:
        if role_map is None or name in seen:
            return False
        seen.add(name)
        target = role_map.get("/" + name)
        if not isinstance(target, Name):
            return False
        name = str(target)[1:]
    return True


def _in_circle(name: str, role_map: Dictionary) -> bool:
    current, seen = name, set()
    while True:
        target = role_map.get("/" + current)
        if not isinstance(target, Name):
            return False
        current = str(target)[1:]
        if current == name:
            return True
        if current in seen:
            return False
        seen.add(current)


def map_custom_types(pdf: Pdf) -> RoleMapResult:
    """Map every custom tag name of the document that does not lead to a standard tag."""
    result = RoleMapResult()
    root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(root, Dictionary):
        return result
    role_map = root.get("/RoleMap")
    if not isinstance(role_map, Dictionary):
        role_map = None
    by_name: dict[str, list[Dictionary]] = {}
    stack, seen = list(kids(root)), set()
    while stack:
        element = stack.pop()
        if not is_element(element):
            continue
        if element.is_indirect:
            if element.objgen in seen:
                continue
            seen.add(element.objgen)
        by_name.setdefault(str(element.get("/S"))[1:], []).append(element)
        stack.extend(kids(element))
    if role_map is not None:
        # A standard tag mapped onto itself or into a circle (e.g. /LI -> /LI): standard tags
        # keep their own meaning anyway, so the entry is removed.
        for key in list(role_map.keys()):
            name = str(key)[1:]
            if name in STANDARD_TYPES and _in_circle(name, role_map):
                del role_map[key]
                result.removed.append(name)
    broken = sorted(name for name in by_name if not _resolves(name, role_map))
    if role_map is not None:                                   # names only used inside cycles
        broken += sorted(str(key)[1:] for key in role_map.keys()
                         if str(key)[1:] not in by_name and str(key)[1:] not in STANDARD_TYPES
                         and not _resolves(str(key)[1:], role_map))
    if not broken:
        return result
    if role_map is None:
        role_map = Dictionary()
        root["/RoleMap"] = role_map
    for name in broken:
        tag = guess_by_name(name)
        if tag is None:
            tag = _guess_by_content(by_name.get(name, []))
            result.guessed.append(name)
        role_map["/" + name] = Name("/" + tag)
        result.mapped[name] = tag
    return result


def report_role_map(result: RoleMapResult) -> None:
    """Tell the user which names were mapped; list the guesses for checking."""
    if result.removed:
        report_info(f"Standard tag names that pointed to themselves were cleaned up: {', '.join(result.removed)}.")
    if not result.mapped:
        return
    names = ", ".join(f"{name} → {tag}" for name, tag in sorted(result.mapped.items()))
    report_info(f"Custom tag names now have a standard meaning: {names}.")
    for name in result.guessed:
        tag = result.mapped[name]
        meaning = {"Div": "a group", "P": "a paragraph", "Span": "text inside a line"}.get(tag, tag)
        report_review(f"The tag name '{name}' does not say what it is, so it was treated as {meaning}. Please check.")
