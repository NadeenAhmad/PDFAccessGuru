"""
Figures as a reader sees them (1.1): a chart, diagram or plot is one picture, whether it is drawn
with lines and shapes (vector drawings), cut into many small raster pieces, or both.

Drawings and pictures that touch or overlap are grouped into one figure region; parts of one
figure that lie close together (sub-plots, the labels between them) join it. Short text inside
or right next to a region (axis ticks, axis titles, legends, labels in a diagram) belongs to the
figure; paragraphs, captions, headings and table text never do. Regions that are only a line, a
frame or a box around text, a table grid, a page background or tiny (a dot, a small symbol) stay
decoration.

layout.py calls group_figures() for every page, marking.py gives every drawing, picture and label
inside a region the region's MCID, and builder.py writes the region's bounding box (/BBox, which
the picture description fix uses to crop the region).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pymupdf as fitz
from pikepdf import Array, Dictionary, Name

TOUCH = 3.0          # drawings and pictures closer than this touch
NEAR = 8.0           # parts of one figure (sub-plots with their labels) closer than this belong together
LABEL_REACH = 14.0   # labels this close to the drawn part of a figure belong to it
GRID_GAP = 24.0      # pictures of the same size in a row or grid this close are one figure
TINY = 40.0          # a region that fits into TINY x TINY points is a dot, symbol or icon
MIN_SHARE = 0.005    # ... and so is a region covering less than this share of the page
THIN = 12.0          # thinner than this: a line or rule, never a figure on its own
_LABEL_WORDS = 6     # labels are short: at most this many words ...
_LABEL_CHARS = 40    # ... and letters per line
_TEXT_DENSE = 0.35   # text covering more than this share of a region: a text box, not a figure
_GRID_DENSE = 0.15   # ... or, for regions of straight lines only, a table grid

_CAPTION = re.compile(r"^\s*(fig(ure)?\.?|abb(ildung)?\.?|image|bild|chart|diagram|grafik|foto|photo|"
                      r"table|tab\.|tabelle|listing|algorithm)\s*\d", re.IGNORECASE)
_WORD = re.compile(r"[^\W\d_]{2,}")
_NUMBERED_HEADING = re.compile(r"^\s*((?:\d+|[A-Z])(?:\.\d+)*)\.?\s+[A-Z][A-Za-z]{2,}")


@dataclass
class _Part:
    rect: fitz.Rect                # the drawn part and its labels
    drawings: int = 0
    straight: bool = True          # only straight horizontal/vertical lines and rectangles
    pictures: list = field(default_factory=list)   # raster Figure items
    labels: list = field(default_factory=list)     # text items that are labels of the figure
    drawn: fitz.Rect | None = None                 # the drawn part only
    near: list = field(default_factory=list)       # labels next to the drawn part (tick labels)

    def __post_init__(self) -> None:
        if self.drawn is None:
            self.drawn = fitz.Rect(self.rect)

    def take(self, other: "_Part") -> None:
        self.rect = _union(self.rect, other.rect)
        self.drawn = _union(self.drawn, other.drawn)
        self.drawings += other.drawings
        self.straight = self.straight and other.straight
        self.pictures += other.pictures
        self.labels += other.labels
        self.near += other.near


def _is_straight(drawing: dict) -> bool:
    for entry in drawing.get("items", []):
        kind = entry[0]
        if kind == "l":
            start, end = entry[1], entry[2]
            if abs(start.x - end.x) > 0.5 and abs(start.y - end.y) > 0.5:
                return False
        elif kind == "c":
            return False
        elif kind == "qu" and not entry[1].is_rectangular:
            return False
    return True


def _visible(drawing: dict) -> bool:
    fill, stroke = drawing.get("fill"), drawing.get("color")
    if fill is None and stroke is None:
        return False
    if stroke is None and fill is not None and all(value > 0.99 for value in fill):
        return False                                     # white on white: a background or an eraser
    return (drawing.get("fill_opacity") or 1) > 0.01 or (drawing.get("stroke_opacity") or 1) > 0.01


def _expanded(rect: fitz.Rect, by: float) -> fitz.Rect:
    return fitz.Rect(rect.x0 - by, rect.y0 - by, rect.x1 + by, rect.y1 + by)


def _union(a: fitz.Rect, b: fitz.Rect) -> fitz.Rect:
    """Both rectangles together (also for lines, which PyMuPDF treats as empty)."""
    return fitz.Rect(min(a.x0, b.x0), min(a.y0, b.y0), max(a.x1, b.x1), max(a.y1, b.y1))


def _touching(a: fitz.Rect, b: fitz.Rect, by: float) -> bool:
    return a.x0 - by <= b.x1 and b.x0 - by <= a.x1 and a.y0 - by <= b.y1 and b.y0 - by <= a.y1


def _clusters(rects: list[fitz.Rect], by: float) -> list[list[int]]:
    """Indexes of rectangles that touch each other (directly or through others), via a grid."""
    parent = list(range(len(rects)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    cell = 24.0
    grid: dict[tuple[int, int], list[int]] = {}
    for index, rect in enumerate(rects):
        area = _expanded(rect, by)
        for gx in range(int(area.x0 // cell), int(area.x1 // cell) + 1):
            for gy in range(int(area.y0 // cell), int(area.y1 // cell) + 1):
                for other in grid.get((gx, gy), ()):
                    if find(other) != find(index) and _touching(rects[other], rect, by):
                        parent[find(other)] = find(index)
                grid.setdefault((gx, gy), []).append(index)
    groups: dict[int, list[int]] = {}
    for index in range(len(rects)):
        groups.setdefault(find(index), []).append(index)
    return list(groups.values())


def _center(rect: fitz.Rect) -> fitz.Point:
    return fitz.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)


def _long(text: str) -> bool:
    """More words than a label has (only real words count, not numbers or unknown signs)."""
    words = _WORD.findall(text)
    return len(words) > _LABEL_WORDS or sum(len(word) for word in words) > _LABEL_CHARS


def _is_prose_item(item) -> bool:
    """A paragraph, caption or heading: text that never belongs to a figure."""
    return item.kind in ("P", "LI") and any(
        _long(line.text) or _CAPTION.match(line.text) or _NUMBERED_HEADING.match(line.text) for line in item.lines)


def _is_label_item(item, body: float) -> bool:
    """Short text that can be part of a figure: no sentence, caption, heading or list."""
    if item.kind not in ("P", "LI") or not item.lines or len(item.lines) > 12:
        return False
    for line in item.lines:
        if _long(line.text):
            return False
        if _CAPTION.match(line.text) or _NUMBERED_HEADING.match(line.text):
            return False
        if line.size > body * 1.6:                      # a title, not a label
            return False
    return True


_CACHE: list = [None, []]          # the page whose drawings were read last, and its drawings


def _drawings(page: fitz.Page) -> list[dict]:
    """The painted paths of a page, each with the rectangle where it can be seen (inside its clip)."""
    if _CACHE[0] is not page:
        try:
            entries = page.get_drawings(extended=True)
        except Exception:
            entries = []
        drawings, clips = [], {}
        for entry in entries:
            level = entry.get("level", 0)
            if entry.get("type") in ("clip", "group"):
                for deeper in [key for key in clips if key >= level]:
                    del clips[deeper]
                if entry.get("type") == "clip" and entry.get("scissor") is not None:
                    clips[level] = fitz.Rect(entry["scissor"])
                continue
            rect = fitz.Rect(entry["rect"])
            for key, scissor in clips.items():
                if key < level:
                    rect = fitz.Rect(max(rect.x0, scissor.x0), max(rect.y0, scissor.y0),
                                     min(rect.x1, scissor.x1), min(rect.y1, scissor.y1))
            if rect.x0 > rect.x1 or rect.y0 > rect.y1:
                continue                                 # clipped away: not visible
            entry["rect"] = rect
            drawings.append(entry)
        _CACHE[0], _CACHE[1] = page, drawings
    return _CACHE[1]


def drop_chart_tables(page: fitz.Page, tables: list, data: dict) -> list:
    """
    A chart with grid lines can look like a table to the table finder. A "table" with a data
    line or curve across it (or pictures covering much of it) and text in at most half of its
    cells is a chart: its Table and Cell items are dropped, so it becomes a figure.
    """
    if not tables:
        return tables
    drawings = _drawings(page)
    centers = [_center(fitz.Rect(line["bbox"])) for block in data.get("blocks", []) for line in block.get("lines", [])
               if any(span["text"].strip() for span in line["spans"])]
    pictures = [fitz.Rect(block["bbox"]) for block in data.get("blocks", []) if block.get("type") == 1]
    charts = set()
    for table in (item for item in tables if item.kind == "Table"):
        area = _expanded(table.rect, 2)
        cells = [item for item in tables if item.kind == "Cell" and item.table == table.table]
        filled = sum(1 for cell in cells if any(cell.rect.contains(point) for point in centers))
        if not cells or filled > len(cells) * 0.5:
            continue
        data_line = any(
            _visible(drawing) and not _is_straight(drawing) and area.contains(fitz.Rect(drawing["rect"]))
            and (drawing["rect"].width >= table.rect.width * 0.25 or drawing["rect"].height >= table.rect.height * 0.25)
            for drawing in drawings)
        covered = sum(abs(picture & table.rect) for picture in pictures)
        if data_line or covered >= abs(table.rect) * 0.2:
            charts.add(table.table)
    return [item for item in tables if item.table not in charts]


def _join_picture_grids(regions: list[_Part], holds_prose) -> list[_Part]:
    """
    Pictures of the same size set out in a row or a grid with small gaps (at least three, no
    text in between) are one figure: e.g. the panels of a figure. Two pictures side by side
    may be two figures (one in each column), so they stay apart.
    """
    photos = [region for region in regions if region.pictures]
    if len(photos) < 3 or len(photos) > 200:
        return regions
    parent = list(range(len(photos)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def similar(a: float, b: float) -> bool:
        return abs(a - b) <= 0.1 * max(a, b, 1.0)

    for i, a in enumerate(photos):
        for j in range(i + 1, len(photos)):
            b = photos[j]
            ra, rb = a.drawn, b.drawn
            if not (similar(ra.width, rb.width) and similar(ra.height, rb.height)):
                continue
            if not (abs(ra.y0 - rb.y0) <= 3 or abs(ra.x0 - rb.x0) <= 3):
                continue
            gap = max(rb.x0 - ra.x1, ra.x0 - rb.x1, rb.y0 - ra.y1, ra.y0 - rb.y1)
            if 0 <= gap <= GRID_GAP and not holds_prose(_union(ra, rb)):
                parent[find(i)] = find(j)
    groups: dict[int, list[_Part]] = {}
    for index, photo in enumerate(photos):
        groups.setdefault(find(index), []).append(photo)
    joined = {id(photo) for group in groups.values() if len(group) >= 3 for photo in group}
    result = [region for region in regions if id(region) not in joined]
    for group in groups.values():
        if len(group) >= 3:
            for photo in group[1:]:
                group[0].take(photo)
            result.append(group[0])
    return result


def is_tiny(rect: fitz.Rect, page_rect: fitz.Rect, picture: bool = False) -> bool:
    """
    A dot, a symbol or a small icon: too small to be a figure of its own. Drawings must also
    cover a small share of the page; a photo may be small (a strip of small photos in a table).
    """
    if (rect.width < TINY and rect.height < TINY) or min(rect.width, rect.height) < THIN:
        return True
    return not picture and abs(rect) < abs(page_rect) * MIN_SHARE


def group_figures(page: fitz.Page, items: list, table_areas: list[fitz.Rect], body: float) -> list:
    """
    Replace the raster Figure items of a page and its vector drawings by figure regions: one
    Figure item per region, holding its labels as lines. Returns the new list of items.
    """
    from pdfaccessguru.tagging.layout import Item

    page_rect = page.rect
    page_area = abs(page_rect)
    drawings = _drawings(page)

    text_items = [item for item in items if item.kind in ("P", "LI")]
    labels = [item for item in text_items if _is_label_item(item, body)]
    prose_lines = [line.rect for item in text_items if _is_prose_item(item) for line in item.lines]
    prose_centers = [_center(rect) for rect in prose_lines]

    def in_table(rect: fitz.Rect) -> bool:
        point = _center(rect)
        return any(_expanded(area, 2).contains(point) for area in table_areas)

    def holds_prose(rect: fitz.Rect) -> bool:
        area = _expanded(rect, 1)
        return any(area.contains(point) for point in prose_centers)

    # 1. the parts: visible drawings (no page backgrounds or frames, no table rules, no boxes
    #    around text) and raster pictures
    parts: list[_Part] = []
    for drawing in drawings:
        rect = fitz.Rect(drawing["rect"])
        if not _visible(drawing) or not page_rect.intersects(_expanded(rect, 1)):
            continue
        if abs(rect & page_rect) > page_area * 0.6 or in_table(rect):
            continue                                     # a page background or frame, a table rule
        if rect.width > 2 * THIN and rect.height > 2 * THIN and holds_prose(rect):
            continue                                     # a box, frame or background behind text
        parts.append(_Part(rect, 1, _is_straight(drawing)))
    pictures = [item for item in items if item.kind == "Figure"]
    for item in pictures:
        parts.append(_Part(fitz.Rect(item.rect), 0, False, [item]))
    if not parts:
        return items

    # 2. parts that touch form one cluster
    regions: list[_Part] = []
    for group in _clusters([part.rect for part in parts], TOUCH):
        merged = _Part(fitz.Rect(parts[group[0]].rect), 0, True)
        for index in group:
            merged.take(parts[index])
        regions.append(merged)
    regions = _join_picture_grids([region for region in regions if not in_table(region.drawn)], holds_prose) + \
        [region for region in regions if in_table(region.drawn)]       # pictures in table cells stay apart

    # 3. clusters that are more than a line grow: labels inside or next to them join, and
    #    clusters close to each other join, as long as no paragraph text lies in between
    def substantial(region: _Part) -> bool:
        return min(region.drawn.width, region.drawn.height) >= THIN or bool(region.pictures)

    def grows(region: _Part) -> bool:
        return substantial(region) and not in_table(region.drawn)   # pictures in table cells stay apart

    def joins(label, region: _Part) -> str | None:
        """
        A label joins a figure if it lies inside the drawn part, or (for drawings, not photos)
        right next to it: tick labels, axis titles, a legend. Measured from the drawn part only,
        so labels cannot reach from one to the next (the rows of a table).
        """
        inside = _expanded(region.drawn, 1)
        if all(inside.contains(_center(line.rect)) for line in label.lines):
            return "inside"
        if not region.drawings:
            return None                                  # text next to a photo is not part of it
        if any(line.size > body * 1.05 or (line.bold and line.size >= body * 0.95) for line in label.lines):
            return None                                  # a heading or title near a figure stays text
        reach = _expanded(region.drawn, LABEL_REACH)
        if all(reach.intersects(line.rect) for line in label.lines):
            return "near"
        # one step further: an axis title next to the tick labels (never a chain of labels)
        if region.near and all(any(_expanded(near.rect, NEAR).intersects(line.rect) for near in region.near)
                               for line in label.lines):
            return "beyond"
        return None

    free_labels = list(labels)
    for _ in range(8):
        changed = False
        growing = [region for region in regions if grows(region)]
        for region in growing:
            for label in list(free_labels):
                how = joins(label, region)
                if how and not holds_prose(_union(region.rect, label.rect)):
                    if how == "near":
                        region.near.append(label)
                    region.labels.append(label)
                    region.rect = _union(region.rect, label.rect)
                    free_labels.remove(label)
                    changed = True
        absorbed: set[int] = set()
        for region in growing:
            if id(region) in absorbed:
                continue
            for other in regions:
                if other is region or id(other) in absorbed or not _touching(other.rect, region.rect, NEAR):
                    continue
                if other.pictures and in_table(other.drawn):
                    continue
                if holds_prose(_union(other.rect, region.rect)):
                    continue
                region.take(other)
                absorbed.add(id(other))
                changed = True
        regions = [region for region in regions if id(region) not in absorbed]
        if not changed:
            break

    # 4. keep the regions that are figures
    figures: list[_Part] = []
    for region in regions:
        rect = region.rect
        if not substantial(region) or is_tiny(rect & page_rect, page_rect, picture=not region.drawings) \
                or holds_prose(rect):
            continue
        if not region.pictures and region.drawings < 2:
            continue                                     # one shape alone: a box or a mark
        text_area = sum(abs(line.rect) for label in region.labels for line in label.lines)
        density = text_area / max(abs(rect), 1.0)
        if density > _TEXT_DENSE or (region.straight and not region.pictures and density > _GRID_DENSE):
            continue                                     # a text box or a table grid
        if not region.pictures and region.straight and region.drawings < 6:
            continue                                     # a frame, a shaded box or a few rules
        figures.append(region)

    taken_pictures = {id(picture) for region in figures for picture in region.pictures}
    taken_labels = {id(label) for region in figures for label in region.labels}
    result = []
    for item in items:
        if id(item) in taken_pictures or id(item) in taken_labels:
            continue
        if item.kind == "Figure" and is_tiny(item.rect, page_rect, picture=True):
            item.kind = "Decoration"                     # a dot, symbol or small icon on its own
        result.append(item)
    for region in figures:
        lines = [line for label in region.labels for line in label.lines]
        figure = Item("Figure", page.number, fitz.Rect(region.rect) & page_rect, lines,   # the visible part
                      text=" ".join(line.text for line in lines))
        figure.vector = region.drawings > 0
        result.append(figure)
    return result


# ---------------------------------------------------------------- used by marking.py and builder.py

def owner_of_area(items: list, rect: fitz.Rect) -> int | None:
    """The figure whose region holds this drawing, picture or form (index into items)."""
    best, best_area = None, None
    for index, item in enumerate(items):
        if item.kind == "Figure" and _expanded(item.rect, 2).contains(rect):
            area = abs(item.rect)
            if best_area is None or area < best_area:
                best, best_area = index, area
    return best


def label_owner(items: list, point: fitz.Point) -> int | None:
    """The figure whose label text is drawn at this point (index into items)."""
    for index, item in enumerate(items):
        if item.kind != "Figure" or not item.lines or not _expanded(item.rect, 3).contains(point):
            continue
        for line in item.lines:
            margin = max(1.0, line.rect.height * 0.25)
            if fitz.Rect(line.rect.x0 - 1, line.rect.y0 - margin, line.rect.x1 + 1, line.rect.y1 + margin).contains(point):
                return index
    return None


def region_owner(items: list, point: fitz.Point) -> int | None:
    """A figure with labels whose region contains this point (text not found on any line)."""
    for index, item in enumerate(items):
        if item.kind == "Figure" and item.lines and item.rect.contains(point):
            return index
    return None


def layout_attributes(rect: fitz.Rect, page: fitz.Page) -> Dictionary:
    """Layout attributes with the bounding box in PDF coordinates (PDF/UA asks for it on Figures)."""
    box = fitz.Rect(rect) * ~page.transformation_matrix
    box.normalize()
    return Dictionary(O=Name.Layout, BBox=Array([round(value, 2) for value in (box.x0, box.y0, box.x1, box.y1)]))


def add_figure_attributes(element: Dictionary, item, page: fitz.Page) -> None:
    """
    A Figure or Formula element gets its bounding box. Descriptions (/Alt) are written later by
    the picture and formula fixes (rules 7.3-1 and 7.7-1), which crop the page at this box.
    """
    element["/A"] = layout_attributes(item.rect, page)
