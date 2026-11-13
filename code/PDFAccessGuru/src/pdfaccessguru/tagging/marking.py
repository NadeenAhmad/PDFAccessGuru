"""
Marking page content (Phase 6): every text, picture and drawing operator of a page is wrapped in
a marked-content sequence. Text and pictures get an MCID of the item they belong to (found by
where they are drawn on the page); lines and shapes become decoration (Artifact), as do
recognised headers, footers and page numbers, unless they lie in a figure region (figures.py):
then they, and the labels in it, get the Figure's MCID. Text is never hidden: text that matches no item
joins the nearest one. Marked content does not change how a page looks.

The position of each text operator is followed with a small interpreter of the graphics and text
state (q/Q, cm, BT/ET, Tm, Td, TD, T*, Tf, Tc, Tw, Tz, TL, Ts and the advance of shown text).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pymupdf as fitz
import pikepdf
from pikepdf import Array, Dictionary, Name, Operator

from pdfaccessguru.tagging import figures
from pdfaccessguru.tagging.layout import Item, is_decoration

_SHOW = {"Tj", "TJ", "'", '"'}
_PATH_START = {"m", "re"}
_PATH = {"m", "l", "c", "v", "y", "h", "re"}
_PAINT = {"S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "n"}
_CLOSE_BEFORE = {"q", "Q", "BT", "ET", "BMC", "BDC", "EMC", "BX", "EX"}
_TAG = {"P": "P", "LI": "LBody", "Caption": "Caption", "Figure": "Figure", "Formula": "Formula"}
_NOT_TEXT = ("Figure", "Decoration", "Table")         # items that text never belongs to


def _form_has_text(form, depth: int = 0) -> bool:
    """Whether a form XObject shows text, also through forms nested inside it."""
    try:
        if b"BT" in form.read_bytes():
            return True
    except Exception:
        return True                                  # unreadable: never treat it as decoration
    resources = form.get("/Resources")
    xobjects = resources.get("/XObject") if isinstance(resources, Dictionary) else None
    if depth > 8 or not isinstance(xobjects, Dictionary):
        return False
    return any(isinstance(x, pikepdf.Stream) and x.get("/Subtype") == Name.Form and _form_has_text(x, depth + 1)
               for x in xobjects.values())


def _path_area(instructions, start: int, matrix: fitz.Matrix) -> fitz.Rect | None:
    """Where the path that starts at this instruction is drawn on the page (None if unknown)."""
    xs, ys = [], []
    for position in range(start, len(instructions)):
        operands, operator = instructions[position]
        name = str(operator)
        if name not in _PATH:
            break
        try:
            values = [float(value) for value in operands]
        except (TypeError, ValueError):
            return None
        if name == "re" and len(values) == 4:
            x, y, width, height = values
            values = [x, y, x + width, y + height, x, y + height, x + width, y]
        for index in range(0, len(values) - 1, 2):
            point = fitz.Point(values[index], values[index + 1]) * matrix
            xs.append(point.x)
            ys.append(point.y)
    if not xs:
        return None
    return fitz.Rect(min(xs), min(ys), max(xs), max(ys))


def _distance(item: Item, point: fitz.Point) -> tuple[float, float]:
    """How far a point is from the nearest line of an item (0 on the line); between lines that both
    hold it, the lower one wins (a line of text, not the tall line of a drop cap next to it)."""
    return min(((point.distance_to(line.rect), line.rect.height) for line in item.lines),
               default=(point.distance_to(item.rect), item.rect.height))


def _shows_only_label(items: list[Item], target, origin: fitz.Point, end: fitz.Point) -> bool:
    """Whether a text operator shows only the marker of a list item (it then gets an Lbl of its own;
    a marker shown together with the text stays in the body)."""
    if not isinstance(target, int) or items[target].kind != "LI" or items[target].label is None:
        return False
    label = items[target].label
    height = max(label.height, 4)
    return (label.x0 - 2 <= origin.x <= label.x1 and label.y0 - height <= origin.y <= label.y1 + height * 0.5
            and min(origin.x, end.x) >= label.x0 - 2 and max(origin.x, end.x) <= label.x1 + max(1.5, height * 0.5))


def _matrix(values) -> fitz.Matrix:
    return fitz.Matrix(*[float(v) for v in values])


class _Widths:
    """Glyph widths of a font (in text space units / 1000), enough to follow the text position."""

    def __init__(self, font) -> None:
        self.two_byte = isinstance(font, Dictionary) and font.get("/Subtype") == Name.Type0
        self.widths: dict[int, float] = {}
        self.default = 500.0
        if not isinstance(font, Dictionary):
            return
        if self.two_byte:
            descendant = font.get("/DescendantFonts")
            cid_font = descendant[0] if isinstance(descendant, Array) and len(descendant) else None
            if isinstance(cid_font, Dictionary):
                self.default = float(cid_font.get("/DW", 1000))
                entries = list(cid_font.get("/W") or [])
                index = 0
                while index < len(entries):
                    start = int(entries[index])
                    following = entries[index + 1] if index + 1 < len(entries) else None
                    if isinstance(following, Array):
                        for offset, width in enumerate(following):
                            self.widths[start + offset] = float(width)
                        index += 2
                    elif index + 2 < len(entries):
                        for code in range(start, int(following) + 1):
                            self.widths[code] = float(entries[index + 2])
                        index += 3
                    else:
                        break
        else:
            first = int(font.get("/FirstChar", 0))
            for offset, width in enumerate(font.get("/Widths") or []):
                self.widths[first + offset] = float(width)
            descriptor = font.get("/FontDescriptor")
            if isinstance(descriptor, Dictionary) and "/MissingWidth" in descriptor:
                self.default = float(descriptor.MissingWidth)

    def codes(self, data: bytes) -> list[int]:
        if self.two_byte:
            return [data[i] << 8 | data[i + 1] for i in range(0, len(data) - 1, 2)]
        return list(data)

    def width(self, code: int) -> float:
        return self.widths.get(code, self.default)


@dataclass
class _State:
    ctm: fitz.Matrix = field(default_factory=lambda: fitz.Matrix(1, 0, 0, 1, 0, 0))
    font: object = None
    size: float = 0.0
    char_spacing: float = 0.0
    word_spacing: float = 0.0
    scale: float = 1.0
    leading: float = 0.0
    rise: float = 0.0


@dataclass
class PageMarks:
    mcids: dict[int, list[int]] = field(default_factory=dict)   # item index -> MCIDs
    extra_figures: list[Item] = field(default_factory=list)      # pictures the layout did not list
    labels: dict[int, list[int]] = field(default_factory=dict)  # list item index -> MCIDs of its marker (Lbl)


def mark_page(pdf: pikepdf.Pdf, page: pikepdf.Page, fitz_page: fitz.Page, items: list[Item]) -> PageMarks:
    """Rewrite the page content with marked-content sequences. Returns the MCIDs per item."""
    marks = PageMarks()
    resources = page.obj.get("/Resources")
    fonts = resources.get("/Font") if isinstance(resources, Dictionary) else None
    xobjects = resources.get("/XObject") if isinstance(resources, Dictionary) else None
    to_page = fitz_page.transformation_matrix
    page_area = abs(fitz_page.rect)
    widths_cache: dict[str, _Widths] = {}

    state = _State()
    stack: list[_State] = []
    text_matrix = fitz.Identity
    line_matrix = fitz.Identity
    out: list[tuple] = []
    open_target: object = None               # item index, "artifact", or None
    existing: list[str] = []                 # tags of marked content already in the page
    next_mcid = 0
    last_text_target: int | None = None
    last_text_y: float | None = None

    def close() -> None:
        nonlocal open_target
        if open_target is not None:
            out.append(([], Operator("EMC")))
            open_target = None

    def open_for(target) -> None:
        nonlocal open_target, next_mcid
        if target == open_target:
            return
        close()
        if target == "artifact":
            out.append(([Name.Artifact], Operator("BMC")))
        elif isinstance(target, tuple):                          # ("label", item): the marker of a list item
            out.append(([Name.Lbl, Dictionary(MCID=next_mcid)], Operator("BDC")))
            marks.labels.setdefault(target[1], []).append(next_mcid)
            next_mcid += 1
        else:
            item = items[target]
            if item.kind == "H":
                tag = f"H{item.level}"
            elif item.kind == "Cell":
                tag = "TH" if item.header else "TD"
            else:
                tag = _TAG.get(item.kind, "P")
            out.append(([Name("/" + tag), Dictionary(MCID=next_mcid)], Operator("BDC")))
            marks.mcids.setdefault(target, []).append(next_mcid)
            next_mcid += 1
        open_target = target

    def inside_artifact() -> bool:
        return "/Artifact" in existing

    def text_target(point: fitz.Point):
        nonlocal last_text_target, last_text_y
        label = figures.label_owner(items, point)                 # a label of a chart or diagram
        if label is not None:
            last_text_target, last_text_y = label, point.y
            return label
        hits = [i for i, item in enumerate(items) if item.kind not in _NOT_TEXT and item.contains(point)]
        content_hits = [i for i in hits if items[i].kind != "Artifact"]
        cell_hits = [i for i in content_hits if items[i].kind == "Cell"]
        content_hits = cell_hits + [i for i in content_hits if i not in cell_hits]   # a cell wins
        if content_hits:
            # otherwise the item whose line is nearest (a big heading's wide margin must not take the line below)
            target = content_hits[0] if cell_hits else min(content_hits, key=lambda i: _distance(items[i], point))
        elif hits:
            return "artifact"                                     # a recognised header, footer or page number
        elif figures.region_owner(items, point) is not None:
            target = figures.region_owner(items, point)           # more text inside a labelled figure
        elif last_text_target is not None and last_text_y is not None and abs(point.y - last_text_y) < 3:
            target = last_text_target                             # the same line as the text before
        else:
            candidates = [i for i, item in enumerate(items) if item.kind not in _NOT_TEXT + ("Artifact",)]
            if not candidates:
                items.append(Item("P", fitz_page.number, fitz.Rect(point, point)))
                candidates = [len(items) - 1]
            target = min(candidates, key=lambda i: point.distance_to(items[i].rect))
        last_text_target, last_text_y = target, point.y
        return target

    def picture_target(rect: fitz.Rect):
        region = figures.owner_of_area(items, rect)
        if region is not None:
            return region                                         # a piece of a figure
        if is_decoration(rect, fitz_page.rect) or figures.is_tiny(rect, fitz_page.rect, picture=True):
            return "artifact"                                     # line, dot, stripe or page background
        best, overlap = None, 0.0
        for i, item in enumerate(items):
            if item.kind in ("Figure", "Decoration"):
                shared = abs(item.rect & rect)
                if shared > overlap:
                    best, overlap = i, shared
        if best is not None:
            return "artifact" if items[best].kind == "Decoration" else best
        items.append(Item("Figure", fitz_page.number, fitz.Rect(rect)))
        marks.extra_figures.append(items[-1])
        return len(items) - 1

    def placement(matrix: fitz.Matrix) -> fitz.Rect:
        corners = [fitz.Point(x, y) * matrix * to_page for x, y in ((0, 0), (1, 0), (0, 1), (1, 1))]
        return fitz.Rect(min(p.x for p in corners), min(p.y for p in corners),
                         max(p.x for p in corners), max(p.y for p in corners))

    def advance(data: bytes, widths: _Widths) -> float:
        total = 0.0
        for code in widths.codes(data):
            total += (widths.width(code) / 1000.0 * state.size + state.char_spacing
                      + (state.word_spacing if code == 32 and not widths.two_byte else 0.0)) * state.scale
        return total

    in_path = False
    instructions = pikepdf.parse_content_stream(page)
    for position, (operands, operator) in enumerate(instructions):
        name = str(operator)
        if name in _CLOSE_BEFORE:
            close()
        if name == "INLINE IMAGE":
            if not inside_artifact():
                open_for(picture_target(placement(state.ctm)))
            out.append((operands, operator))
            continue
        if name in _PATH_START and not in_path and not inside_artifact():
            # lines and shapes are decoration, unless they are part of a figure (a chart, a diagram)
            path_area = _path_area(instructions, position, state.ctm * to_page)
            owner = figures.owner_of_area(items, path_area) if path_area is not None else None
            open_for("artifact" if owner is None else owner)
            in_path = True
        elif name == "sh" and not inside_artifact():
            open_for("artifact")
        if name in _PAINT:
            in_path = False

        if name == "q":
            stack.append(_State(fitz.Matrix(state.ctm), state.font, state.size, state.char_spacing,
                                state.word_spacing, state.scale, state.leading, state.rise))
        elif name == "Q":
            if stack:
                state = stack.pop()
        elif name == "cm":
            state.ctm = _matrix(operands) * state.ctm
        elif name in ("BMC", "BDC"):
            existing.append(str(operands[0]))
        elif name == "EMC":
            if existing:
                existing.pop()
        elif name == "BT":
            text_matrix = line_matrix = fitz.Identity
        elif name == "Tf":
            font_name = str(operands[0])
            if font_name not in widths_cache:
                widths_cache[font_name] = _Widths(fonts.get(font_name) if isinstance(fonts, Dictionary) else None)
            state.font, state.size = widths_cache[font_name], float(operands[1])
        elif name == "Tc":
            state.char_spacing = float(operands[0])
        elif name == "Tw":
            state.word_spacing = float(operands[0])
        elif name == "Tz":
            state.scale = float(operands[0]) / 100.0
        elif name == "TL":
            state.leading = float(operands[0])
        elif name == "Ts":
            state.rise = float(operands[0])
        elif name in ("Td", "TD"):
            if name == "TD":
                state.leading = -float(operands[1])
            line_matrix = fitz.Matrix(1, 0, 0, 1, float(operands[0]), float(operands[1])) * line_matrix
            text_matrix = fitz.Matrix(line_matrix)
        elif name == "Tm":
            line_matrix = _matrix(operands)
            text_matrix = fitz.Matrix(line_matrix)
        elif name == "T*":
            line_matrix = fitz.Matrix(1, 0, 0, 1, 0, -state.leading) * line_matrix
            text_matrix = fitz.Matrix(line_matrix)

        if name in _SHOW:
            if name in ("'", '"'):
                line_matrix = fitz.Matrix(1, 0, 0, 1, 0, -state.leading) * line_matrix
                text_matrix = fitz.Matrix(line_matrix)
                if name == '"':
                    state.word_spacing, state.char_spacing = float(operands[0]), float(operands[1])
            origin = fitz.Point(0, state.rise) * text_matrix * state.ctm * to_page
            widths = state.font or _Widths(None)
            shown = 0.0
            for operand in (operands[0] if name == "TJ" else operands[-1:]):
                if isinstance(operand, (pikepdf.String, bytes)):
                    shown += advance(bytes(operand), widths)
                else:
                    try:                                      # a TJ number moves the next glyph back
                        shown -= float(operand) / 1000.0 * state.size * state.scale
                    except (TypeError, ValueError):
                        pass
            if not inside_artifact():
                target = text_target(origin)
                end = fitz.Point(shown, state.rise) * text_matrix * state.ctm * to_page
                open_for(("label", target) if _shows_only_label(items, target, origin, end) else target)
            text_matrix = fitz.Matrix(1, 0, 0, 1, shown, 0) * text_matrix
        elif name == "Do" and isinstance(xobjects, Dictionary):
            xobject = xobjects.get(str(operands[0]))
            if not inside_artifact() and isinstance(xobject, pikepdf.Stream):
                if xobject.get("/Subtype") == Name.Image:
                    open_for(picture_target(placement(state.ctm)))
                else:
                    bbox = xobject.get("/BBox", [0, 0, 1, 1])
                    form = _matrix(xobject.get("/Matrix", [1, 0, 0, 1, 0, 0])) * state.ctm
                    x0, y0, x1, y1 = (float(v) for v in bbox)
                    corners = [fitz.Point(x, y) * form * to_page for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
                    rect = fitz.Rect(min(p.x for p in corners), min(p.y for p in corners),
                                     max(p.x for p in corners), max(p.y for p in corners))
                    has_text = _form_has_text(xobject)
                    inside = [i for i, item in enumerate(items) if item.kind not in ("Artifact",)
                              and abs(item.rect & rect) > 0.5 * max(abs(item.rect), 1)]
                    region = figures.owner_of_area(items, rect & fitz_page.rect)
                    if region is not None:
                        open_for(region)                          # a chart or diagram drawn in a form
                    elif has_text and inside:
                        # text is never hidden inside a figure: a text item comes first
                        open_for(next((i for i in inside if items[i].kind != "Figure"), inside[0]))
                    elif any(items[i].kind == "Figure" for i in inside):
                        open_for(next(i for i in inside if items[i].kind == "Figure"))
                    else:
                        open_for("artifact")
        out.append((operands, operator))
        if name == "ET":
            last_text_target = None
    close()
    page.obj["/Contents"] = pdf.make_stream(pikepdf.unparse_content_stream(out))
    return marks
