"""
Colour contrast (Phase 9): text that is hard to read because its colour is too close to what is
behind it. WCAG 2.2, success criterion 1.4.3 (level AA): at least 4.5:1, or 3:1 for large text
(18 pt, or 14 pt bold).

Finding it is always done and reported. Changing colours only happens when the user switches it
on, because many templates (for example official ones) must keep their colours. A fix changes
only the colour of the text itself, keeps its hue and makes it just dark (or light) enough, in the
colour system the text already uses (grey, RGB or CMYK). Backgrounds, pictures and the layout are
never touched; every letter must stay where it was, or the fix is undone. Text on pictures or
colour gradients, and text in special colour systems, is only reported, to check by hand.

How the background is measured: the page is drawn a second time without its text, so the colour
behind every word is known exactly, even for light grey text on a light background.

Safety rules, found on real files:
- Text that is practically invisible (below 1.3:1, e.g. white on white) is often hidden on purpose
  (left-overs of saved web pages); it is reported, never made visible.
- Text keeps its side: light text only gets lighter, dark text only darker. If that cannot reach
  the minimum (white text is already as light as it gets), the place is reported instead.
- Text on pictures or gradients counts as "check by eye" only if it could actually be too faint
  (it stands out clearly against the main colour behind it otherwise).
"""

from __future__ import annotations

import colorsys
import io
from dataclasses import dataclass, field

import fitz
import pikepdf
from pikepdf import Dictionary, Name, Operator

NORMAL, LARGE = 4.5, 3.0
HIDDEN = 1.3                          # below this, text is treated as hidden on purpose
_SHOW = {"Tj", "TJ", "'", '"'}
_ZOOM = 1.5
_MAX_PLACES_LISTED = 8


@dataclass
class Place:
    page: int                         # 1-based
    text: str
    ratio: float
    color: tuple[int, int, int]
    background: tuple[int, int, int]
    large: bool
    rect: tuple[float, float, float, float]   # page coordinates, top-left origin


@dataclass
class ContrastResult:
    switched_on: bool
    low_before: int = 0               # places below the minimum before any change
    fixed: int = 0                    # places that now reach the minimum
    low: list[Place] = field(default_factory=list)          # still below the minimum
    unclear: int = 0                  # text on pictures or gradients: check by hand
    hidden: int = 0                   # practically invisible text (left alone)
    undone: str = ""                  # why the colour changes were undone, if they were

    def as_dict(self) -> dict:
        return {"switched_on": self.switched_on, "low_before": self.low_before, "fixed": self.fixed,
                "unclear": self.unclear, "hidden": self.hidden, "undone": self.undone,
                "low": [{"page": p.page, "text": p.text, "ratio": round(p.ratio, 2), "large": p.large}
                        for p in self.low[:_MAX_PLACES_LISTED]],
                "low_count": len(self.low), "pages": sorted({p.page for p in self.low})}


# ------------------------------------------------------------------------------- measuring

def _luminance(rgb) -> float:
    def channel(value: float) -> float:
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(a, b) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _without_text(data: bytes) -> bytes:
    """The same pages with every text operator removed (to see the background behind the text)."""
    with pikepdf.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            try:
                operations = [(o, op) for o, op in pikepdf.parse_content_stream(page) if str(op) not in _SHOW]
                page.obj["/Contents"] = pdf.make_stream(pikepdf.unparse_content_stream(operations))
            except Exception:
                continue
        buffer = io.BytesIO()
        pdf.save(buffer)
        return buffer.getvalue()


def find_low_contrast(data: bytes) -> tuple[list[Place], int, int]:
    """Text below the WCAG AA minimum; how much text sits on pictures or gradients and could be
    too faint (unclear); and how much text is practically invisible (hidden, not counted as low)."""
    low: list[Place] = []
    unclear = hidden = 0
    with fitz.open(stream=data, filetype="pdf") as document, \
            fitz.open(stream=_without_text(data), filetype="pdf") as backgrounds:
        for number, page in enumerate(document):
            spans = [span for block in page.get_text("dict")["blocks"] for line in block.get("lines", [])
                     for span in line["spans"] if any(c.isalnum() for c in span["text"])
                     and span.get("alpha", 255) > 0]
            if not spans:
                continue
            pixmap = backgrounds[number].get_pixmap(matrix=fitz.Matrix(_ZOOM, _ZOOM), alpha=False)
            width, height, stride = pixmap.width, pixmap.height, pixmap.stride
            samples = pixmap.samples
            for span in spans:
                x0, y0, x1, y1 = (int(v * _ZOOM) for v in span["bbox"])
                x0, y0, x1, y1 = max(0, x0), max(0, y0), min(width, x1), min(height, y1)
                if x1 - x0 < 2 or y1 - y0 < 2:
                    continue
                pixels = [tuple(samples[y * stride + x * 3: y * stride + x * 3 + 3])
                          for y in range(y0, y1, 2) for x in range(x0, x1, 2)]
                buckets: dict[tuple, list] = {}
                for pixel in pixels:
                    buckets.setdefault((pixel[0] >> 4, pixel[1] >> 4, pixel[2] >> 4), []).append(pixel)
                main = max(buckets.values(), key=len)
                background = tuple(round(sum(p[i] for p in main) / len(main)) for i in range(3))
                color = ((span["color"] >> 16) & 255, (span["color"] >> 8) & 255, span["color"] & 255)
                large = span["size"] >= 18 or (span["size"] >= 14 and span["flags"] & 16)
                minimum = LARGE if large else NORMAL
                ratio = contrast_ratio(color, background)
                if len(main) < 0.85 * len(pixels):          # a picture or a gradient behind the text
                    if ratio < minimum:
                        unclear += 1
                    continue
                if ratio < HIDDEN:
                    hidden += 1
                elif ratio < minimum:
                    low.append(Place(number + 1, " ".join(span["text"].split())[:60], ratio, color, background,
                                     bool(large), tuple(span["bbox"])))
    return low, unclear, hidden


# ------------------------------------------------------------------------------- fixing

def better_color(color, background, minimum: float) -> tuple[int, int, int] | None:
    """The same hue, just dark (or light) enough to reach the minimum contrast. Dark text only gets
    darker and light text only lighter; None if the minimum cannot be reached that way."""
    darker = _luminance(color) <= _luminance(background)
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in color))
    for step in range(1, 101):
        lightness = l * (1 - step / 100) if darker else l + (1 - l) * step / 100
        candidate = tuple(round(c * 255) for c in colorsys.hls_to_rgb(h, lightness, s))
        if contrast_ratio(candidate, background) >= minimum + 0.1:
            return candidate
    return None


_DEVICE = {"/DeviceGray": "gray", "/DeviceRGB": "rgb", "/DeviceCMYK": "cmyk"}
_ICC_KIND = {1: "gray", 3: "rgb", 4: "cmyk"}


def _space_kind(name: str, resources) -> str | None:
    """gray, rgb or cmyk for device colour spaces and colour profiles (ICC); None for anything else
    (spot colours, patterns, calibrated spaces: their text is only reported)."""
    if name in _DEVICE:
        return _DEVICE[name]
    spaces = resources.get("/ColorSpace") if isinstance(resources, Dictionary) else None
    space = spaces.get(name) if isinstance(spaces, Dictionary) else None
    if isinstance(space, pikepdf.Array) and len(space) == 2 and space[0] == Name.ICCBased:
        return _ICC_KIND.get(int(space[1].get("/N", 0)))
    return None


def _fill_kind(fill: list, resources) -> tuple[str, str] | None:
    """(gray/rgb/cmyk, operator that sets the colour) of the current fill colour, or None."""
    if not fill:
        return "gray", "g"
    operands, operator = fill[-1]
    name = str(operator)
    if name in ("g", "rg", "k"):
        return {"g": "gray", "rg": "rgb", "k": "cmyk"}[name], name
    if name in ("sc", "scn"):
        spaces = [o for o, op in fill if str(op) == "cs"]
        kind = _space_kind(str(spaces[-1][0]), resources) if spaces else None
        if kind and operands and not any(isinstance(v, pikepdf.Name) for v in operands):   # a pattern has a name
            try:
                [float(v) for v in operands]          # numbers (pikepdf gives Decimal for 0.346)
            except (TypeError, ValueError):
                return None
            return kind, name
    return None


def _fill_rgb(fill: list, kind: str) -> tuple[float, float, float] | None:
    """The colour (0-255) the current fill operators set."""
    if not fill:
        return (0.0, 0.0, 0.0)
    try:
        values = [float(v) for v in fill[-1][0]]
    except (TypeError, ValueError):
        return None
    if kind == "gray" and len(values) == 1:
        return (values[0] * 255,) * 3
    if kind == "rgb" and len(values) == 3:
        return tuple(v * 255 for v in values)
    if kind == "cmyk" and len(values) == 4:
        c, m, y, k = values
        return tuple(255 * (1 - min(1.0, v + k)) for v in (c, m, y))
    return None


def _fill_operator(kind: str, operator: str, rgb) -> tuple[list, Operator]:
    """Operators that set the new colour in the same colour system the text already uses."""
    r, g, b = (c / 255 for c in rgb)
    if kind == "gray":
        values = [round(0.2126 * r + 0.7152 * g + 0.0722 * b, 4)]
    elif kind == "rgb":
        values = [round(r, 4), round(g, 4), round(b, 4)]
    else:
        k = 1 - max(r, g, b)
        values = [0, 0, 0, 1] if k >= 1 else [round((1 - r - k) / (1 - k), 4), round((1 - g - k) / (1 - k), 4),
                                              round((1 - b - k) / (1 - k), 4), round(k, 4)]
    return values, Operator(operator)


def _same_color(fill: list, kind: str, operator: str, color) -> bool:
    """Only text drawn in exactly the colour of the low-contrast place is changed (other text on the
    same line keeps its colour). Profiles and CMYK are shown converted, so they get some leeway."""
    rgb = _fill_rgb(fill, kind)
    if rgb is None:
        return False
    tolerance = 4 if operator in ("g", "rg") else 40
    return all(abs(a - b) <= tolerance for a, b in zip(rgb, color))


def _recolor_page(pdf: pikepdf.Pdf, page: pikepdf.Page, fitz_page: fitz.Page, places: list[Place]) -> int:
    """Give the text operators of the low-contrast places their new colour. Returns how many."""
    from pdfaccessguru.tagging.marking import _matrix, _State, _Widths

    resources = page.obj.get("/Resources")
    fonts = resources.get("/Font") if isinstance(resources, Dictionary) else None
    to_page = fitz_page.transformation_matrix
    state, stack = _State(), []
    fill: list = []                         # operators that set the current fill colour ([] = black)
    render_mode = 0
    text_matrix = line_matrix = fitz.Identity
    widths_cache: dict[str, _Widths] = {}
    out: list = []
    changed = 0
    for operands, operator in pikepdf.parse_content_stream(page):
        name = str(operator)
        if name == "q":
            stack.append((_State(fitz.Matrix(state.ctm), state.font, state.size, state.char_spacing,
                                 state.word_spacing, state.scale, state.leading, state.rise), list(fill), render_mode))
        elif name == "Q" and stack:
            state, fill, render_mode = stack.pop()
        elif name == "cm":
            state.ctm = _matrix(operands) * state.ctm
        elif name in ("g", "rg", "k"):
            fill = [(operands, operator)]
        elif name == "cs":
            fill = [(operands, operator)]
        elif name in ("sc", "scn"):
            fill = [op for op in fill if str(op[1]) == "cs"] + [(operands, operator)]
        elif name == "Tr":
            render_mode = int(operands[0])
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
            kind = _fill_kind(fill, resources)
            place = next((p for p in places if p.rect[0] - 2 <= origin.x <= p.rect[2] + 2
                          and p.rect[1] - 2 <= origin.y <= p.rect[3] + 2), None)
            new_fill = None
            if place is not None and render_mode == 0 and kind is not None and _same_color(fill, *kind, place.color):
                target = better_color(place.color, place.background, LARGE if place.large else NORMAL)
                new_fill = _fill_operator(*kind, target) if target is not None else None
            if new_fill is not None:
                out.append(new_fill)
            out.append((operands, operator))
            if new_fill is not None:
                out.extend(fill or [([0], Operator("g"))])     # back to the colour the page had set
                changed += 1
            widths = state.font or _Widths(None)
            shown = 0.0
            for operand in (operands[0] if name == "TJ" else operands[-1:]):
                if isinstance(operand, (pikepdf.String, bytes)):
                    for code in widths.codes(bytes(operand)):
                        shown += (widths.width(code) / 1000.0 * state.size + state.char_spacing
                                  + (state.word_spacing if code == 32 and not widths.two_byte else 0.0)) * state.scale
                else:
                    try:
                        shown -= float(operand) / 1000.0 * state.size * state.scale
                    except (TypeError, ValueError):
                        pass
            text_matrix = fitz.Matrix(1, 0, 0, 1, shown, 0) * text_matrix
            continue
        out.append((operands, operator))
    if changed:
        page.obj["/Contents"] = pdf.make_stream(pikepdf.unparse_content_stream(out))
    return changed


def check_and_fix_contrast(document, switched_on: bool) -> ContrastResult:
    """
    Measure the contrast of all text in the working document; with the option switched on, fix
    what can be fixed safely. The fix is undone if any letter moved or changed.
    """
    from pdfaccessguru.pipeline.transaction import compare_glyph_positions

    result = ContrastResult(switched_on)
    before = document.snapshot()
    low, result.unclear, result.hidden = find_low_contrast(before)
    result.low_before = len(low)
    if not switched_on or not low:
        result.low = low
        return result
    by_page: dict[int, list[Place]] = {}
    for place in low:
        by_page.setdefault(place.page, []).append(place)
    with fitz.open(stream=before, filetype="pdf") as layout:
        for number, places in by_page.items():
            try:
                _recolor_page(document.pdf, document.pdf.pages[number - 1], layout[number - 1], places)
            except Exception:
                continue
    after = document.snapshot()
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as work:
        path = Path(work) / "after.pdf"
        path.write_bytes(after)
        reason = compare_glyph_positions(before, str(path))
    if reason:
        document.restore(before)
        result.undone, result.low = reason, low
        return result
    still_low, _, _ = find_low_contrast(after)
    key = lambda place: (place.page, place.text, round(place.rect[0]), round(place.rect[1]))
    if {key(place) for place in still_low} - {key(place) for place in low}:
        document.restore(before)                     # some other text got harder to read: undo all
        result.undone, result.low = "other text would have become harder to read", low
        return result
    result.low = still_low
    result.fixed = max(0, len(low) - len(still_low))
    return result
