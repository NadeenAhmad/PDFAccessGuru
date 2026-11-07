"""Where the content of a structure element sits on the page, and what text it shows."""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass

import pdfplumber
from pikepdf import Array, Dictionary, Name, Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import is_element, kids, page_of


@dataclass(frozen=True)
class Box:
    page: int
    x0: float
    top: float
    x1: float
    bottom: float

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def center(self) -> tuple[float, float]:
        return (self.x0 + self.x1) / 2, (self.top + self.bottom) / 2

    def union(self, other: "Box") -> "Box":
        return Box(self.page, min(self.x0, other.x0), min(self.top, other.top),
                   max(self.x1, other.x1), max(self.bottom, other.bottom))

    def vertical_overlap(self, other: "Box") -> float:
        """Shared height as a share of the smaller of the two heights (0 to 1)."""
        if self.page != other.page:
            return 0.0
        shared = min(self.bottom, other.bottom) - max(self.top, other.top)
        smaller = min(self.height, other.height)
        return max(0.0, shared) / smaller if smaller > 0 else 0.0

    def contains_point(self, x: float, y: float) -> bool:
        return self.x0 <= x <= self.x1 and self.top <= y <= self.bottom


@dataclass
class _Page:
    signature: str
    boxes: dict[int, Box]
    texts: dict[int, str]
    spaced: dict[int, str] | None = None     # the same text with spaces where letters have a gap


def _signature(page: Dictionary) -> str:
    contents = page.get("/Contents")
    streams = list(contents) if isinstance(contents, Array) else [contents]
    digest = hashlib.sha1()
    for stream in streams:
        try:
            digest.update(stream.read_raw_bytes())
        except Exception:
            digest.update(b"?")
    return digest.hexdigest()


class Layout:
    """
    Reads positions and text of marked content with pdfplumber. Pages are read only when a
    repair needs them. The parsed pages are kept between repairs and re-read when the page
    content changed in between (repairs of the structure tree never change it).
    """

    _cache: dict[int, dict[int, _Page]] = {}

    def __init__(self, pdf: Pdf):
        self.pdf = pdf
        self._page_index = {page.obj.objgen: index for index, page in enumerate(pdf.pages)}
        self._pages = Layout._cache.setdefault(id(pdf), {})
        if len(Layout._cache) > 4:                      # keep only recent documents
            for key in list(Layout._cache)[:-4]:
                del Layout._cache[key]
        self._snapshot: bytes | None = None
        self._plumber = None                 # one open document per snapshot (opening is slow)

    def _page(self, index: int) -> _Page | None:
        page_obj = self.pdf.pages[index].obj
        signature = _signature(page_obj)
        cached = self._pages.get(index)
        if cached is not None and cached.signature == signature:
            return cached
        if self._snapshot is None:
            buffer = io.BytesIO()
            self.pdf.save(buffer)
            self._snapshot = buffer.getvalue()
        boxes: dict[int, Box] = {}
        texts: dict[int, list[str]] = {}
        spaced: dict[int, list[str]] = {}
        last: dict[int, dict] = {}
        try:
            if self._plumber is None:
                self._plumber = pdfplumber.open(io.BytesIO(self._snapshot))
            page = self._plumber.pages[index]
            for objects in page.objects.values():
                for obj in objects:
                    mcid = obj.get("mcid")
                    if not isinstance(mcid, int):
                        continue
                    box = Box(index, float(obj["x0"]), float(obj["top"]), float(obj["x1"]), float(obj["bottom"]))
                    boxes[mcid] = boxes[mcid].union(box) if mcid in boxes else box
                    if obj.get("object_type") == "char":
                        char = obj.get("text") or ""
                        texts.setdefault(mcid, []).append(char)
                        # many PDFs have no space characters, only gaps: a space where the gap is wide
                        parts, previous = spaced.setdefault(mcid, []), last.get(mcid)
                        if previous is not None and parts and not parts[-1].isspace() and not char.isspace():
                            size = max(float(obj.get("size") or 0), 1.0)
                            if abs(obj["top"] - previous["top"]) > size * 0.5 or obj["x0"] - previous["x1"] > size * 0.15:
                                parts.append(" ")
                        parts.append(char)
                        last[mcid] = obj
            page.close()                                   # free the parsed objects of this page
        except Exception:
            return None
        parsed = _Page(signature, boxes, {mcid: "".join(parts) for mcid, parts in texts.items()},
                       {mcid: "".join(parts) for mcid, parts in spaced.items()})
        self._pages[index] = parsed
        return parsed

    def _refs(self, item, owner) -> list[tuple[int, int]]:
        """(page index, MCID) of all marked content shown by an item."""
        if is_element(item):
            return [ref for kid in kids(item) for ref in self._refs(kid, item)]
        if isinstance(item, int):
            page = page_of(owner)
        elif isinstance(item, Dictionary) and item.get("/Type") == Name("/MCR") and "/Stm" not in item:
            page = item.get("/Pg") or page_of(owner)
            item = item.get("/MCID")
        else:
            return []
        index = self._page_index.get(page.objgen) if isinstance(page, Dictionary) else None
        return [] if index is None or item is None else [(index, int(item))]

    def box(self, item, owner=None) -> Box | None:
        """Bounding box of everything the item shows, or None if unknown or on several pages."""
        refs = self._refs(item, owner)
        if not refs or len({page for page, _ in refs}) > 1:
            return None
        result = None
        for page_index, mcid in refs:
            page = self._page(page_index)
            box = page.boxes.get(mcid) if page else None
            if box is None:
                return None
            result = box if result is None else result.union(box)
        return result

    def text(self, item, owner=None, spaced: bool = False) -> str:
        """The text an item shows. spaced=True puts spaces where letters have a wide gap (for texts
        people read: descriptions, previews); the default keeps the letters as the repairs expect."""
        parts = []
        for page_index, mcid in self._refs(item, owner):
            page = self._page(page_index)
            if page is not None:
                parts.append((page.spaced or {}).get(mcid, "") if spaced else page.texts.get(mcid, ""))
        if spaced:
            return " ".join(" ".join(part.split()) for part in parts if part.strip())
        return " ".join(part for part in parts if part).strip()
