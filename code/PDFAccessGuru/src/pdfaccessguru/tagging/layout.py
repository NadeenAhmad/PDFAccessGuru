"""
Reading a page like a person (Phase 6): which text is a heading (and which level), a paragraph,
a list item, a caption, a header or footer; where the pictures are; and the reading order,
also on pages with two columns. Uses only PyMuPDF's text and image positions.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

import pymupdf as fitz

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.pictures import CAPTION_START
from pdfaccessguru.tagging.figures import drop_chart_tables, group_figures
from pdfaccessguru.tagging.formulas import find_formulas

_NUMBERED_HEADING = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2})*)\.?\s+\S")      # "2 Methods", "2.3.1 Data"
_ROMAN_HEADING = re.compile(r"^\s*([IVX]{1,4})\.\s+\S")                      # "IV. RESULTS"
_LETTER_HEADING = re.compile(r"^\s*([A-Z])\.\s+\S")                          # "A. Setup" (or "A. Appendix")
_PAGE_NUMBER = re.compile(r"^\s*(?:page|seite)?\s*(\d+|[ivxlcdm]+)(\s*(/|of|von)\s*\d+)?\s*$", re.IGNORECASE)
_TABLE_CAPTION = re.compile(r"^\s*(table|tab\.|tabelle)\s*(\d|[IVXLC]+\b|[A-Z]\.?\d)", re.IGNORECASE)
# "Figure 3:", "Fig. 3.", "FIG. 1.", "Abb. 2", "Listing 1", "Algorithm 2" (tables: _TABLE_CAPTION)
_FIGURE_CAPTION = re.compile(r"^\s*(fig(ure)?s?\.?|abb(ildung)?\.?|listing|algorithm(us)?|scheme|exhibit)"
                             r"\s*([A-Z]?\d+(\.\d+)*[a-z]?)", re.IGNORECASE)
# after the label: "Figure 3: ...", "Table 2. ...", "Fig. 1 | ...", "Figure 2 (a) - ...", or nothing ("TABLE I")
_CAPTION_DELIMITER = re.compile(r"^\s*(\(\w{1,3}\)\s*)?([:.|–—-]|$)")
# "Figure 3 shows ..." / "Tabelle 2 zeigt ...": a sentence that mentions a figure, not its caption
_MENTION = re.compile(r"^\s*(shows?|illustrates?|presents?|summari[sz]es?|gives?|lists?|depicts?|compares?|contains?|"
                      r"displays?|reports?|provides?|describes?|indicates?|demonstrates?|highlights?|plots?|is|are|"
                      r"was|were|has|have|and|or|in|of|to|from|with|zeigt|stellt|enthält|gibt|fasst|verdeutlicht|"
                      r"ist|sind|und|oder)\b", re.IGNORECASE)
# unnumbered headings that sit at section level whatever their size
_SECTION_NAMES = re.compile(r"^\s*((\d{1,2}|[IVX]{1,4})\.?\s+)?(abstract|summary|introduction|background|related work|"
                            r"methods?|methodology|materials and methods|results|discussion|conclusions?|"
                            r"conclusions? and future work|future work|limitations|acknowledge?ments?|references|"
                            r"bibliography|appendix( [A-Z])?|supplementary (material|information)|author contributions|"
                            r"funding|conflicts? of interest|zusammenfassung|kurzfassung|einleitung|einführung|fazit|ausblick|"
                            r"danksagung|literatur|literaturverzeichnis|quellenverzeichnis|anhang|inhaltsverzeichnis|"
                            r"contents|table of contents)\s*:?\s*$", re.IGNORECASE)
# list markers: bullets that always start an item, ones that need a second item, and numbers
_STRONG_BULLETS = set("•‣▪▫●○◦⁃∙➢►▸▹■□◆◇❖✓✔➤➔◾◽⦁")
_WEAK_BULLETS = set("-–—*·→⇒»")
_NUMBER_MARKER = re.compile(r"^\s*(?:\((\d{1,3}|[a-zA-Z]|[ivxlc]{1,5})\)|(\d{1,3}|[a-zA-Z]|[ivxlc]{1,5})[.)]"
                            r"|\[(\d{1,3})\])(?=\s|$)")
_SYMBOL_FONTS = ("symbol", "wingding", "dingbat", "webding")


@dataclass
class Line:
    rect: fitz.Rect
    text: str
    size: float
    bold: bool
    horizontal: bool = True               # written in the main direction of the page (not a side stamp)
    label: fitz.Rect | None = None        # the list marker, when it is drawn as a span of its own
    lead_bold: bool = False               # the first words are bold, the rest not ("Fig. 1 The ...")
    symbol_marker: bool = False           # the line starts with one character of a symbol font (a bullet)


@dataclass
class Item:
    kind: str                     # H, P, LI, Figure, Caption, Artifact, Decoration, Table, Cell
    page: int
    rect: fitz.Rect
    lines: list[Line] = field(default_factory=list)
    level: int = 0                # heading level 1-6
    text: str = ""
    table: int = -1               # cells: which table, row and column; header row; column span
    row: int = -1
    col: int = -1
    header: bool = False
    col_span: int = 1
    row_span: int = 1
    depth: int = 0                  # list items: nesting depth (0 = top level)
    label: fitz.Rect | None = None  # list items: the marker, when it is drawn on its own (Lbl)
    block: int = -1                 # the text block the item was read from

    def contains(self, point: fitz.Point, margin: float = 2.0) -> bool:
        if self.kind in ("Figure", "Cell"):
            area = fitz.Rect(self.rect)
            area.x0 -= margin; area.y0 -= margin; area.x1 += margin; area.y1 += margin
            return area.contains(point)
        for line in self.lines:
            height = max(line.rect.height, 4)
            area = fitz.Rect(line.rect.x0 - margin, line.rect.y0 - height * 0.5,
                             line.rect.x1 + margin, line.rect.y1 + height * 0.5)
            if area.contains(point):
                return True
        return False


def _lines_of(block: dict, main: tuple[int, int] = (1, 0)) -> list[Line]:
    """The lines of a text block; `main` is the direction most text of the page is written in
    ((0, -1) or (0, 1) on a page turned by 90 degrees)."""
    lines = []
    for line in block.get("lines", []):
        spans = [span for span in line["spans"] if span["text"].strip()]
        if not spans:
            continue
        text = " ".join(" ".join(span["text"].split()) for span in spans).strip()
        chars = sum(len(span["text"].strip()) for span in spans)
        size = sum(span["size"] * len(span["text"].strip()) for span in spans) / max(chars, 1)
        bold_chars = sum(len(span["text"].strip()) for span in spans if _is_bold(span))
        first = spans[0]["text"].strip()
        symbol = len(first) == 1 and any(name in spans[0]["font"].lower() for name in _SYMBOL_FONTS) \
            and unicodedata.category(first) == "So"
        marker = _marker(first, symbol)
        direction = line.get("dir", (1, 0))
        lines.append(Line(fitz.Rect(line["bbox"]), text, round(size, 1), bold_chars > chars * 0.6,
                          horizontal=(round(direction[0]), round(direction[1])) == main,
                          label=fitz.Rect(spans[0]["bbox"]) if len(spans) > 1 and marker and marker[1] == first else None,
                          lead_bold=len(spans) > 1 and _is_bold(spans[0]) and bold_chars < chars * 0.6,
                          symbol_marker=symbol))
    return lines


def _is_bold(span: dict) -> bool:
    return bool(span["flags"] & 16) or "bold" in span["font"].lower() or "black" in span["font"].lower()


def _marker(text: str, symbol: bool = False) -> tuple[str, str] | None:
    """
    The list marker a text starts with, as (kind, marker): "bullet" (•, ▪, a symbol-font or
    private-use character such as U+F0B7), "dash" (-, –, *, · need a second item to count), "number"
    ("1.", "2)", "(a)", "iv.") or "ref" ("[12]"); None if it starts with none.
    """
    stripped = text.lstrip()
    if not stripped:
        return None
    first = stripped[0]
    if symbol or first in _STRONG_BULLETS or 0xF020 <= ord(first) <= 0xF0FF:
        return "bullet", first
    if first in _WEAK_BULLETS and (len(stripped) == 1 or stripped[1].isspace()):
        return "dash", first
    match = _NUMBER_MARKER.match(stripped)
    if match and not re.fullmatch(r"[A-Z]+\.", match.group(0).strip()):     # "S. Tan": an initial
        return ("ref" if match.group(3) else "number"), match.group(0).strip()
    return None


def _join_markers(blocks: list[list[Line]]) -> None:
    """
    A list marker drawn on its own (a bullet in its own line or block, left of the text) joins
    the line it belongs to: the nearest line to its right at the same height. The marker's place
    is kept as the label of that line.
    """
    lines = [(b, line) for b, block in enumerate(blocks) for line in block]
    for b, line in lines:
        marker = _marker(line.text, line.symbol_marker)
        if marker is None or marker[1] != line.text.strip() or marker[1].startswith("(") or not line.horizontal:
            continue                                       # ("(1)" alone is mostly an equation number)
        middle = (line.rect.y0 + line.rect.y1) / 2
        right = [(other_b, other) for other_b, other in lines if other is not line and other.horizontal
                 and other.rect.y0 - 1 <= middle <= other.rect.y1 + 1
                 and -1 <= other.rect.x0 - line.rect.x1 <= max(40.0, line.rect.height * 3)
                 and _marker(other.text, other.symbol_marker) is None]
        other_b, other = min(right, key=lambda pair: pair[1].rect.x0) if right else (b, None)
        position = next((i for i, kept in enumerate(blocks[b]) if kept is line), None)
        target = next((i for i, kept in enumerate(blocks[other_b]) if kept is other), None)
        if position is None or target is None:              # (already joined)
            continue
        blocks[other_b][target] = Line(line.rect | other.rect, f"{line.text.strip()} {other.text}", other.size,
                                       other.bold, label=fitz.Rect(line.rect), lead_bold=other.lead_bold)
        del blocks[b][position]


def _follows(first: Line, line: Line) -> bool:
    """Whether a line's number follows the one of an item's first line ("4)" then "5)"), or the same dash
    follows a dash, marker under marker."""
    keys = _marker_keys(Item("LI", 0, first.rect, [first])) or []
    following = _marker_keys(Item("LI", 0, line.rect, [line])) or []
    return _aligned(first, line) and any(          # dashes ("-", "·") have no number: the same dash under it
        style == other and (number + 1 == next_number or style.startswith("dash"))
        for style, number in keys for other, next_number in following)


def _aligned(first: Line, second: Line) -> bool:
    """Whether two list markers start at the same place, or end there ("[9]" and "[10]" set flush right)."""
    return abs(first.rect.x0 - second.rect.x0) <= 4 or (
        first.label is not None and second.label is not None and abs(first.label.x1 - second.label.x1) <= 3)


def _size_break(previous: Line, line: Line, body: float) -> bool:
    """A heading in display type and the text below it in one block ("Neutrinos from ..." in 16 pt
    over 11 pt text) are two items; drop caps and formula lines do not split a paragraph."""
    big = previous if previous.size > line.size else line
    letters = sum(char.isalpha() for char in big.text)
    return len(previous.text) > 2 and len(line.text) > 2 and abs(previous.size - line.size) >= 1.5 \
        and big.size >= body * 1.12 and letters >= 3 and letters >= 0.5 * len(big.text.replace(" ", ""))


def _break_before(lines: list[Line], position: int) -> bool:
    """Whether the line before ends a sentence or stops short of the right edge of the block."""
    if position == 0:
        return True
    previous = lines[position - 1]
    left = min(line.rect.x0 for line in lines)
    right = max(line.rect.x1 for line in lines)
    return previous.text.rstrip().endswith((".", ":", ";", "!", "?")) or previous.rect.x1 < right - 0.12 * (right - left)


def _normalized(text: str) -> str:
    return re.sub(r"\d+", "#", text.lower()).strip()


def analyse(document: fitz.Document) -> list[list[Item]]:
    """Items of every page, in reading order."""
    pages = [document[index].get_text("dict") for index in range(document.page_count)]
    sizes: Counter = Counter()
    for data in pages:
        for block in data["blocks"]:
            for line in _lines_of(block):
                sizes[line.size] += len(line.text)
    body = sizes.most_common(1)[0][0] if sizes else 10.0

    # Headers and footers: short lines near the top or bottom that repeat on many pages, and page numbers.
    margins: Counter = Counter()
    for index, data in enumerate(pages):
        height = document[index].rect.height
        for block in data["blocks"]:
            for line in _lines_of(block):
                if line.rect.y1 < height * 0.09 or line.rect.y0 > height * 0.91:
                    margins[_normalized(line.text)] += 1
    # (a two-page handout counts: the line must be on both pages)
    repeated = {text for text, count in margins.items() if count >= max(2, document.page_count * 0.4)}

    # Images repeated at the same place in the header or footer of several pages (logos)
    repeated_images: Counter = Counter()
    for index, data in enumerate(pages):
        height = document[index].rect.height
        for block in data["blocks"]:
            if block["type"] == 1:
                rect = fitz.Rect(block["bbox"])
                if rect.y1 < height * 0.15 or rect.y0 > height * 0.85:
                    repeated_images[tuple(round(v / 4) for v in rect)] += 1
    repeated_logos = {key for key, count in repeated_images.items() if count >= max(3, document.page_count * 0.4)}

    result: list[list[Item]] = []
    heading_sizes: set[float] = set()
    for index, data in enumerate(pages):
        page = document[index]
        height = page.rect.height
        items: list[Item] = []
        tables = drop_chart_tables(page, _tables(page, index), data)     # a chart with grid lines is no table
        table_areas = [item.rect for item in tables if item.kind == "Table"]
        directions: Counter = Counter()
        for block in data["blocks"]:
            for line in block.get("lines", []):
                directions[(round(line["dir"][0]), round(line["dir"][1]))] += sum(len(s["text"]) for s in line["spans"])
        main = directions.most_common(1)[0][0] if directions else (1, 0)
        text_blocks = {number: [line for line in _lines_of(block, main)
                                if not any(area.contains(fitz.Point((line.rect.x0 + line.rect.x1) / 2,
                                                                    (line.rect.y0 + line.rect.y1) / 2)) for area in table_areas)]
                       for number, block in enumerate(data["blocks"]) if block["type"] != 1}
        _join_markers(list(text_blocks.values()))
        for number, block in enumerate(data["blocks"]):
            if block["type"] == 1:
                rect = fitz.Rect(block["bbox"])
                if rect.width > 4 and rect.height > 4:
                    decorative = is_decoration(rect, page.rect) or \
                        tuple(round(v / 4) for v in rect) in repeated_logos
                    items.append(Item("Decoration" if decorative else "Figure", index, rect))
                continue
            lines = text_blocks[number]
            if not lines:
                continue
            current: Item | None = None
            for position, line in enumerate(lines):
                in_margin = line.rect.y1 < height * 0.09 or line.rect.y0 > height * 0.91
                page_number = _PAGE_NUMBER.match(line.text) and (line.rect.y1 < height * 0.12 or line.rect.y0 > height * 0.85)
                if page_number or (in_margin and _normalized(line.text) in repeated):
                    items.append(Item("Artifact", index, fitz.Rect(line.rect), [line], text=line.text))
                    current = None
                    continue
                looks_like_heading = line.size >= body * 1.12 or (line.bold and len(lines) == 1)
                marker = _marker(line.text, line.symbol_marker) if line.horizontal else None
                # a bullet always starts an item; a number or dash only where a new line may begin
                starts_item = marker is not None and len(line.text) > len(marker[1]) + 1 and \
                    (marker[0] != "bullet" or re.search(r"[^\W_]{2}", line.text[2:])) and \
                    (marker[0] == "bullet" or (not looks_like_heading and (
                        _break_before(lines, position) or (current is not None and current.kind == "LI"
                                                           and _follows(current.lines[0], line)))))
                if current is None or (starts_item and current.kind in ("P", "LI")) or _size_break(current.lines[-1], line, body) or \
                        (current.kind == "LI" and line.rect.x0 < current.lines[0].rect.x0 - 3):
                    current = Item("LI" if starts_item else "P", index, fitz.Rect(line.rect), [line],
                                   label=line.label if starts_item else None, block=number)
                    items.append(current)
                else:
                    current.lines.append(line)
                    current.rect |= line.rect
        items = group_figures(page, items, table_areas, body)          # charts, diagrams, pictures
        items = find_formulas(page, data, items, body)                 # display equations
        _check_lists(items, body)                                       # after figures took their labels
        # merge list-item continuation blocks (indented text right below an item, no marker)
        merged: list[Item] = []
        for item in items:
            previous = merged[-1] if merged else None
            if (previous is not None and previous.kind == "LI" and item.kind == "P"
                    and -2 < item.rect.y0 - previous.rect.y1 < previous.lines[-1].rect.height * 0.8
                    and previous.rect.x0 + 3 < item.rect.x0 < previous.rect.x1):
                previous.lines.extend(item.lines)
                previous.rect |= item.rect
                continue
            merged.append(item)
        _nest_lists(merged)
        for item in list(merged):
            item.text = " ".join(line.text for line in item.lines)
            if item.kind == "P":
                _classify_text(item, body, heading_sizes)
            last = item.lines[-1] if item.kind == "H" and len(item.lines) > 1 else None
            if last is not None and len(last.text) <= 2 and last.size > _size(item) * 1.5:
                item.lines.pop()                         # the drop cap of the paragraph below is no part of it
                item.rect = fitz.Rect(item.lines[0].rect)
                for line in item.lines[1:]:
                    item.rect |= line.rect
                item.text = " ".join(line.text for line in item.lines)
                merged.insert(merged.index(item) + 1, Item("P", index, fitz.Rect(last.rect), [last], text=last.text,
                                                           block=item.block))
            if item.kind == "H" and (((item.rect.y1 < height * 0.12 or item.rect.y0 > height * 0.88) and _size(item) < body)
                                     or item.rect.y0 > height * 0.92):
                item.kind = "P"                          # a running head in small type ("1 Introduction"), a footer
        # a caption written over several lines or blocks is one caption
        captioned: list[Item] = []
        for item in merged:
            previous = captioned[-1] if captioned else None
            if previous is not None and previous.kind == "Caption" and item.kind in ("P", "H") \
                    and _continues_caption(previous, item, body):
                previous.lines.extend(item.lines)
                previous.rect |= item.rect
                previous.text += " " + item.text
                continue
            captioned.append(item)
        merged = captioned
        # a heading written over two lines (two blocks) is one heading
        joined: list[Item] = []
        for item in merged:
            previous = joined[-1] if joined else None
            if (previous is not None and previous.kind == item.kind == "H"
                    and abs(max(l.size for l in previous.lines) - max(l.size for l in item.lines)) < 0.5
                    and 0 <= item.rect.y0 - previous.rect.y1 < previous.lines[-1].rect.height * 1.2
                    and len(previous.lines) + len(item.lines) <= 3
                    and len(previous.text) + len(item.text) < (200 if _NUMBERED_HEADING.match(previous.text) else 150)):
                previous.lines.extend(item.lines)
                previous.rect |= item.rect
                previous.text += " " + item.text
                continue
            joined.append(item)
        result.append(_place_captions(
            _reading_order(joined + [item for item in tables if item.kind == "Table"], page.rect,
                           [item for item in tables if item.kind == "Cell"]), page.rect))

    _set_heading_levels([item for items in result for item in items if item.kind == "H"], heading_sizes)
    return result


def _set_heading_levels(headings: list[Item], heading_sizes) -> None:
    """
    Numbered headings get their numbering depth ("2 Methods" -> 1, "2.3.1 Data" -> 3, "IV." -> 1
    and "B." -> 2 under roman numbers). A larger, unnumbered heading (the document title) is level 1
    and moves the numbered ones one level down. "Abstract", "References", "Acknowledgments" and
    the like sit at section level; other unnumbered headings take the level of numbered headings of
    the same size; without numbered headings, levels follow the size. At the end, levels never
    skip one (no H1 -> H3) and the first heading is H1.
    """
    roman = sum(1 for item in headings if _ROMAN_HEADING.match(item.text)) >= 2
    numbering: dict[int, int] = {}                      # heading -> depth of its numbering
    for item_id, item in enumerate(headings):
        numbered = _NUMBERED_HEADING.match(item.text)
        if numbered:
            numbering[item_id] = numbered.group(1).count(".") + 1
        elif roman and _ROMAN_HEADING.match(item.text):
            numbering[item_id] = 1
        elif _LETTER_HEADING.match(item.text):
            numbering[item_id] = 2 if roman else 1
    by_depth: dict[int, list[float]] = {}
    for item_id, depth in numbering.items():
        by_depth.setdefault(depth, []).append(_size(headings[item_id]))
    for item_id, depth in list(numbering.items()):         # "1. Baseline" far smaller than "1 Introduction"
        if _size(headings[item_id]) < sorted(by_depth[depth])[len(by_depth[depth]) // 2] - 2:
            del numbering[item_id]                          # (a numbered paragraph label): placed by its size
    depth_sizes: dict[int, list[float]] = {}
    for item_id, depth in numbering.items():
        depth_sizes.setdefault(depth, []).append(_size(headings[item_id]))
    if not depth_sizes:
        ranked: list[float] = []                    # sizes from large to small; nearly equal sizes are one rank
        for size in sorted({_size(item) for item in headings}, reverse=True):
            if not ranked or ranked[-1] - size > 0.6:
                ranked.append(size)
        rank = {item_id: next(r for r, size in enumerate(ranked) if size - _size(item) <= 0.6) + 1
                for item_id, item in enumerate(headings)}
        titles = [item for item_id, item in enumerate(headings) if rank[item_id] == 1]
        section = 2 if len(ranked) > 1 and all(item.page == headings[0].page for item in titles) else 1
        for item_id, item in enumerate(headings):
            item.level = section if _SECTION_NAMES.match(item.text) else min(6, rank[item_id])
    else:
        typical = {depth: sorted(sizes)[len(sizes) // 2] for depth, sizes in depth_sizes.items()}
        top = typical[min(typical)]
        shift = 1 if any(item_id not in numbering and not _SECTION_NAMES.match(item.text) and _size(item) > top + 0.5
                         for item_id, item in enumerate(headings)) else 0
        for item_id, item in enumerate(headings):
            depth = numbering.get(item_id)
            size = _size(item)
            if depth:
                item.level = min(6, depth + shift)
            elif _SECTION_NAMES.match(item.text):
                item.level = 1 + shift
            elif size > top + 0.5:
                item.level = 1                                  # the title above the numbered sections
            else:                                              # same size as a numbered level, else the next one down
                depth = min(typical, key=lambda d: (abs(typical[d] - size), d))
                item.level = min(6, depth + shift if abs(typical[depth] - size) <= 0.5 else
                                 max(typical) + 1 + shift if size < min(typical.values()) else depth + shift)
    # no skipped levels: each heading is at most one level below the one before
    open_levels: list[int] = []
    for item in headings:
        while open_levels and open_levels[-1] >= item.level:
            open_levels.pop()
        open_levels.append(item.level)
        item.level = min(6, len(open_levels))


def _size(item: Item) -> float:
    """The font size of an item, without a drop cap (a large first letter on a line of its own)."""
    sizes = [line.size for line in item.lines if len(line.text) > 2]
    return max(sizes or [line.size for line in item.lines])


def is_decoration(rect: fitz.Rect, page_rect: fitz.Rect) -> bool:
    """Lines, dots, stripes and page backgrounds: drawn for looks, not content."""
    short, long = sorted((rect.width, rect.height))
    if short < 12:
        return True                                        # a thin line or a tiny dot
    if long / short > 12:
        return True                                        # a stripe or bar
    return abs(rect & page_rect) > abs(page_rect) * 0.6    # a page background


def _classify_text(item: Item, body: float, heading_sizes: set[float]) -> None:
    """
    A caption starts with "Figure 3:", "Fig. 3.", "Table 2", "Abb. 1" and the like. A heading is
    short (at most 2 lines and 150 characters; 3 lines and 200 if numbered), bigger or bold, written
    across the page, and does not end like a sentence; "Abstract", "References" and the like on
    a line of their own are headings too. Long bold or big paragraphs stay paragraphs.
    """
    text = item.text
    size = _size(item)
    if _is_caption(item, body):
        item.kind = "Caption"
        return
    letters = sum(ch.isalpha() for ch in text)
    if letters < 2 or letters < 0.5 * len(text.replace(" ", "")) or not all(line.horizontal for line in item.lines) \
            or (_marker(text, item.lines[0].symbol_marker) or ("",))[0] == "bullet" \
            or re.search(r"@\w|https?:|www\.", text):
        return                                   # numbers, formulas, a stamp along the margin, a bullet, an address
    numbered = bool(_NUMBERED_HEADING.match(text) or _ROMAN_HEADING.match(text) or _LETTER_HEADING.match(text))
    short = (len(item.lines) <= 2 and len(text) <= 150) or (numbered and len(item.lines) <= 3 and len(text) <= 200) \
        or (len(item.lines) <= 3 and len(text) <= 150 and size >= body * 1.3)     # a title in display type
    looks_like_sentence_end = text.rstrip().endswith((":", ";", ",")) or \
        (text.rstrip().endswith(".") and len(text.split()) > 3)          # ("Betreuer:" is a label)
    bigger = size >= body * 1.12
    bold_heading = all(line.bold for line in item.lines) and size >= body * 0.95 and len(text) <= 120
    section_name = len(item.lines) == 1 and _SECTION_NAMES.match(text) and size >= body * 0.85
    if section_name or (short and (bigger or bold_heading) and not looks_like_sentence_end):
        item.kind = "H"
        heading_sizes.add(size)


def _is_caption(item: Item, body: float) -> bool:
    """'Figure 3: ...', 'Fig. 1 The setup' (bold label or small type), 'TABLE I' - not 'Figure 3 shows ...'."""
    text = item.text
    match = _TABLE_CAPTION.match(text) or _FIGURE_CAPTION.match(text) or CAPTION_START.match(text)
    if not match:
        return False
    rest = re.sub(r"^[\d.]*\d", "", text[match.end():])        # the rest of the number
    rest = re.sub(r"^[a-z](?=\W)", "", rest)                     # a panel letter: "Figure 5a shows"
    if _MENTION.match(rest):
        return False
    if _CAPTION_DELIMITER.match(rest):
        return True
    # "Fig. 1 The setup": a bold label, small type, or a capital letter where a sentence would go on
    return item.lines[0].lead_bold or _size(item) < body * 0.95 or bool(re.match(r"^\s+[A-ZÄÖÜ]", rest))


def _continues_caption(caption: Item, item: Item, body: float) -> bool:
    """Text right after a caption, in the same type: on the same line, or right below it."""
    last, first = caption.lines[-1], item.lines[0]
    height = max(last.rect.height, 4)
    if abs(first.size - last.size) > 0.6:
        return False
    same_line = abs(first.rect.y0 - last.rect.y0) < height * 0.5 and 0 <= first.rect.x0 - last.rect.x1 + 2 < 3 * height
    gap = first.rect.y0 - last.rect.y1
    below = -2 <= gap <= height * (0.6 if last.size < body * 0.97 else 0.35) \
        and first.rect.x0 < caption.rect.x1 and first.rect.x1 > caption.rect.x0
    return same_line or below


def _check_lists(items: list[Item], body: float) -> None:
    """
    Numbered items count as a list only with a neighbour in sequence on the same page ("1." and
    "2.", "a)" and "b)", "[1]" and "[2]") whose marker starts at the same place; dashes need a
    second dash item. The others are text again and rejoin the text they were split from (a
    paragraph that starts with "(1)", panel labels "(a) Model" in small type).
    """
    list_items = [item for item in items if item.kind == "LI"]   # (blocks are not in reading order yet)
    reverted: list[Item] = []
    if list_items:
        keys = [_marker_keys(item) for item in list_items]
        for position, item in enumerate(list_items):
            if keys[position] is None:                        # a bullet
                continue
            partners = [other for other, other_keys in zip(list_items, keys) if other is not item and other_keys
                        and _aligned(item.lines[0], other.lines[0])
                        and any(style == other_style and (style.startswith("dash") or abs(number - other_number) == 1)
                                for style, number in keys[position] for other_style, other_number in other_keys)]
            text_length = sum(len(line.text) for other in partners + [item] for line in other.lines)
            small_labels = item.lines[0].size < body * 0.95 and not item.lines[0].text.startswith("[") \
                and text_length < 30 * (len(partners) + 1)
            if not partners or small_labels:
                reverted.append(item)
    for item in reverted:
        item.kind, item.label = "P", None
    # rejoin text split off a paragraph
    position = 1
    while position < len(items):
        item, previous = items[position], items[position - 1]
        if any(item is other for other in reverted) and previous.kind in ("P", "LI") and item.block == previous.block >= 0:
            previous.lines.extend(item.lines)
            previous.rect |= item.rect
            del items[position]
            continue
        position += 1


def _marker_keys(item: Item) -> list[tuple[str, int]] | None:
    """
    How an item is numbered, as (style, number): ("#.", 3) for "3.", ("(#)a", 2) for "(b)",
    ("[#]", 12) for "[12]", ("dash-", 0) for "-". "i." may be a letter or a roman number, so it
    has two. None for a bullet.
    """
    marker = _marker(item.lines[0].text, item.lines[0].symbol_marker)
    if marker is None or marker[0] == "bullet":
        return None
    if marker[0] == "dash":
        return [("dash" + marker[1], 0)]
    value = marker[1].strip("()[].")
    style = marker[1].replace(value, "#", 1)
    if value.isdigit():
        return [(style, int(value))]
    keys = []
    if re.fullmatch(r"[ivxlc]+", value.lower()):
        roman = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}
        digits = [roman[char] for char in value.lower()]
        keys.append((style + "r", sum(-a if a < b else a for a, b in zip(digits, digits[1:])) + digits[-1]))
    if len(value) == 1:
        keys.append((style + ("a" if value.islower() else "A"), ord(value.lower()) - ord("a") + 1))
    return keys


def _nest_lists(items: list[Item]) -> None:
    """A list item whose marker is further right than the one of the item before is nested in it."""
    open_x: list[float] = []
    previous: Item | None = None
    for item in items:
        if item.kind != "LI":
            if item.kind not in ("Artifact", "Decoration"):
                open_x, previous = [], None
            continue
        x = item.lines[0].rect.x0
        if previous is not None and (x > open_x[-1] + 60 or item.rect.y0 < previous.rect.y0 - 2):
            open_x = []                                       # the list goes on in the next column
        while open_x and x < open_x[-1] - 4:
            open_x.pop()
        if not open_x or x > open_x[-1] + 8:
            open_x.append(x)
        item.depth = min(len(open_x) - 1, 3)
        previous = item


def _tables(page: fitz.Page, page_index: int) -> list[Item]:
    """Tables PyMuPDF finds from their ruling lines: a Table item, then its cells row by row."""
    found: list[Item] = []
    try:
        tables = page.find_tables().tables
    except Exception:
        return found
    for number, table in enumerate(tables):
        if table.row_count < 2 or table.col_count < 2:
            continue
        header_row = 0 if table.header is not None and not table.header.external else -1
        rows = table.rows
        # Where each row and column starts; a merged cell covers every row/column that starts
        # inside it (a column without any cell of its own is always covered from the left).
        row_tops = [row.bbox[1] for row in rows]
        col_lefts: list[float] = []
        for col_index in range(table.col_count):
            lefts = [row.cells[col_index][0] for row in rows
                     if col_index < len(row.cells) and row.cells[col_index] is not None]
            col_lefts.append(min(lefts) if lefts else (col_lefts[-1] + 1 if col_lefts else 0))
        cells: list[Item] = []
        for row_index, row in enumerate(rows):
            for col_index, cell in enumerate(row.cells):
                if cell is None:                       # part of a merged cell to the left or above
                    continue
                x1, y1 = cell[2], cell[3]
                cells.append(Item("Cell", page_index, fitz.Rect(cell), table=number, row=row_index, col=col_index,
                                  header=row_index == header_row,
                                  col_span=1 + sum(1 for left in col_lefts[col_index + 1:] if left < x1 - 1),
                                  row_span=1 + sum(1 for top in row_tops[row_index + 1:] if top < y1 - 1)))
        if _is_regular(cells, len(rows), table.col_count):
            found.append(Item("Table", page_index, fitz.Rect(table.bbox), table=number))
            found += cells
        # otherwise (overlapping or missing cells) the text stays as paragraphs: a broken
        # table is worse for a screen reader than plain text
    return found


def _is_regular(cells: list[Item], row_count: int, col_count: int) -> bool:
    """Every place of the grid is covered by exactly one cell."""
    covered = [[0] * col_count for _ in range(row_count)]
    for cell in cells:
        for row in range(cell.row, cell.row + cell.row_span):
            for col in range(cell.col, cell.col + cell.col_span):
                if row >= row_count or col >= col_count:
                    return False
                covered[row][col] += 1
    return all(count == 1 for row in covered for count in row)


def _reading_order(items: list[Item], page_rect: fitz.Rect, cells: list[Item] | None = None) -> list[Item]:
    """Top to bottom; on pages with two columns, the left column before the right one. Table
    cells follow their table, row by row."""
    ordered_items = _order(items, page_rect)
    if not cells:
        return ordered_items
    result: list[Item] = []
    for item in ordered_items:
        result.append(item)
        if item.kind == "Table":
            result += [cell for cell in cells if cell.table == item.table]
    return result


def _place_captions(items: list[Item], page_rect: fitz.Rect) -> list[Item]:
    """
    A table caption belongs to the table right above or below it (its `table` is set, so it
    becomes the first or last child of the Table) and is read with it. A figure caption stays next
    to its figure, outside it (a Figure with alternate text hides its children): read right after
    the figure above it, or right before the figure below it. Nothing moves when other text sits
    between them.
    """
    order = list(items)
    for caption in [item for item in items if item.kind == "Caption"]:
        is_table = bool(_TABLE_CAPTION.match(caption.text))
        best = None
        for target in order:
            if target.kind != ("Table" if is_table else "Figure") or is_decoration(target.rect, page_rect) or \
                    any(other.kind == "Caption" and other.table == target.table >= 0 for other in order if is_table):
                continue                                          # (a table has one caption at most)
            overlap = min(caption.rect.x1, target.rect.x1) - max(caption.rect.x0, target.rect.x0)
            if overlap < 0.3 * min(caption.rect.width, target.rect.width):
                continue
            if target.rect.y1 <= caption.rect.y0 + 3:
                gap, above = caption.rect.y0 - target.rect.y1, True       # the target is above the caption
            elif caption.rect.y1 <= target.rect.y0 + 3:
                gap, above = target.rect.y0 - caption.rect.y1, False
            else:
                continue
            if gap > page_rect.height * 0.12 or _text_between(order, caption, target):
                continue
            score = gap + (10 if above == is_table else 0)       # figures above, tables below their caption first
            if best is None or score < best[0]:
                best = (score, target, above)
        if best is None:
            continue
        _, target, above = best
        order.remove(caption)
        position = order.index(target)
        if is_table:
            caption.table = target.table
        if above or is_table:
            position += 1                                         # after the figure / inside the table
            if above:
                while position < len(order) and order[position].kind == "Cell" and order[position].table == target.table:
                    position += 1
        if not is_table:                                          # a figure in pieces: after (before) all of them
            area = fitz.Rect(target.rect)
            step = 0 if above else -1
            while 0 <= position + step < len(order) and _part_of_figure(order[position + step], area, caption):
                area |= order[position + step].rect
                position += 1 if above else -1
        order.insert(position, caption)
    return order


def _part_of_figure(item: Item, area: fitz.Rect, caption: Item) -> bool:
    """Another piece of the same figure (a picture next to it, or text inside it), on the caption's side."""
    if item.kind == "Figure":
        near = fitz.Rect(area.x0 - 5, area.y0 - 5, area.x1 + 5, area.y1 + 5)
        return abs(near & item.rect) > 0 and min(caption.rect.x1, item.rect.x1) > max(caption.rect.x0, item.rect.x0)
    middle = fitz.Point((item.rect.x0 + item.rect.x1) / 2, (item.rect.y0 + item.rect.y1) / 2)
    return item.kind in ("P", "H") and area.contains(middle)


def _text_between(order: list[Item], caption: Item, target: Item) -> bool:
    """Whether other text lies between a caption and a figure or table (outside the figure)."""
    if target.rect.y1 <= caption.rect.y0 + 3:
        top, bottom = target.rect.y1, caption.rect.y0
    else:
        top, bottom = caption.rect.y1, target.rect.y0
    for item in order:
        if item is caption or item.kind not in ("P", "H", "LI", "Caption"):
            continue
        middle = (item.rect.y0 + item.rect.y1) / 2
        inside = target.rect.contains(fitz.Point((item.rect.x0 + item.rect.x1) / 2, middle))
        if top < middle < bottom and not inside and item.rect.x0 < caption.rect.x1 and item.rect.x1 > caption.rect.x0:
            return True
    return False


def _order(items: list[Item], page_rect: fitz.Rect) -> list[Item]:
    content = [item for item in items if item.kind not in ("Artifact", "Decoration")]
    if not content:
        return items
    left_edge = min(item.rect.x0 for item in content)
    right_edge = max(item.rect.x1 for item in content)
    middle = (left_edge + right_edge) / 2
    width = right_edge - left_edge
    narrow = [item for item in content if item.rect.width < width * 0.55]
    left = [item for item in narrow if item.rect.x1 <= middle + 5]
    right = [item for item in narrow if item.rect.x0 >= middle - 5]
    two_columns = len(left) >= 2 and len(right) >= 2 and sum(len(i.text) for i in left + right) > \
        0.5 * sum(len(i.text) for i in content)
    if not two_columns:
        ordered = sorted(content, key=lambda item: (round(item.rect.y0 / 3), item.rect.x0))
    else:
        # full-width items split the page into bands; in each band, left column then right column
        wide = sorted((item for item in content if item not in left and item not in right),
                      key=lambda item: item.rect.y0)
        ordered, top = [], -1.0
        for separator in wide + [None]:
            bottom = separator.rect.y0 if separator is not None else float("inf")
            band = [item for item in left + right if top <= item.rect.y0 < bottom]
            ordered += sorted((i for i in band if i in left), key=lambda i: i.rect.y0)
            ordered += sorted((i for i in band if i in right), key=lambda i: i.rect.y0)
            if separator is not None:
                ordered.append(separator)
                top = separator.rect.y0
    artifacts = [item for item in items if item.kind in ("Artifact", "Decoration")]
    return ordered + artifacts
