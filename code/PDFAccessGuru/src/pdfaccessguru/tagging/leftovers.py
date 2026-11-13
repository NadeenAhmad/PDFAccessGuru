"""
Tagging what a partly tagged file left untagged (1.1).

Many files are tagged only in part: a publisher template tags the article but not the
copyright line, a repository puts a tagged cover sheet in front of an untagged paper, a
program tags the first pages only. The existing tag tree is kept as it is; only the content
that no tag reaches gets its place:

- running headers and footers (lines repeated in the margin of many pages) and page numbers
  become decoration (Artifact), as do pictures that are only lines, stripes or backgrounds
  and logos repeated in the margins (the same rules as tagging a file anew, layout.py);
- other text gets a new structure element of the kind the page layout shows (paragraph,
  heading with its level, list item, caption) with new MCIDs registered in the parent tree;
- other pictures become Figures (the picture fix writes their description later);
- marked content whose MCID no element owns, and elements that hang outside the tree, are
  linked into the tree the same way;
- every new element goes into the existing tree where it is read: right after the element
  that owns the content drawn just before it on the page (else before the first owned
  content of the page, else after the content of the pages before).

Content is only marked, never moved or hidden: a page whose text or character positions
would change is left as it was. A form XObject is tagged as one piece only when it holds no
marked content of its own; content inside a sequence that already has an MCID is never
touched, and content inside other marks (/Span or /OC without an MCID) is marked inside them.
"""

from __future__ import annotations

import io
from collections import Counter
from dataclasses import dataclass, field

import pymupdf as fitz
import pikepdf
from pikepdf import Array, Dictionary, Name, Operator

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import (
    Roles, _parent_tree_slot, is_element, kids, set_kids,
)
from pdfaccessguru.tagging.layout import Item, analyse, is_decoration
from pdfaccessguru.tagging.marking import _matrix, _State, _Widths

_SHOW = {"Tj", "TJ", "'", '"'}
_CLOSE_BEFORE = {"q", "Q", "BT", "ET", "BMC", "BDC", "EMC", "BX", "EX"}
_NOT_TEXT = ("Figure", "Decoration", "Table")
# Elements whose children may be any block: a new paragraph can go next to their children.
_GROUPING = frozenset({"Document", "Part", "Art", "Sect", "Div", "NonStruct", "BlockQuote"})
_HEADINGS = ("H1", "H2", "H3", "H4", "H5", "H6")
_ARTIFACT = "artifact"
_DONE_ATTRIBUTE = "_pdfaccessguru_leftovers_done"


@dataclass
class LeftoverResult:
    pages: int = 0                                              # pages whose content got new marks
    elements: Counter = field(default_factory=Counter)          # new structure elements by type
    artifacts: int = 0                                          # pieces marked as decoration
    linked: int = 0                                             # MCIDs / elements newly linked into the tree
    skipped: Counter = field(default_factory=Counter)           # why pages were left alone

    @property
    def changed(self) -> bool:
        return bool(self.pages or self.linked or sum(self.elements.values()))


@dataclass
class _Plan:
    """One new (or newly linked) structure element of a page."""
    tag: str                                  # P, H, LI, Caption, Figure; "" = link an existing element
    level: int = 0
    mcids: list[int] = field(default_factory=list)
    after: tuple | None = None                # (owner, MCID) of the tagged content drawn just before it
    list_id: int | None = None                # consecutive list items share one L
    existing: Dictionary | None = None        # an element outside the tree, to be linked
    order: int | None = None                  # place of its layout item in the page's reading order


@dataclass
class _PagePlan:
    index: int
    plans: list[_Plan] = field(default_factory=list)
    first_owner: tuple | None = None          # (owner, MCID) of the first tagged content of the page
    owners: list = field(default_factory=list)   # (owner, MCID) of the tagged content, in content order
    new_contents: bytes | None = None         # rewritten content (None: unchanged)
    artifacts: int = 0


# --- the structure tree -------------------------------------------------------------------

def _is_number(item) -> bool:
    if isinstance(item, (Dictionary, Array, Name, pikepdf.String)):
        return False
    try:
        int(item)
        return True
    except (TypeError, ValueError):
        return False


def _position(items: list, element) -> int | None:
    return next((i for i, item in enumerate(items)
                 if isinstance(item, Dictionary) and item.is_indirect and item.objgen == element.objgen), None)


def _number_tree_keys(node, keys: list, seen: set, depth: int = 0) -> None:
    if not isinstance(node, Dictionary) or depth > 32:
        return
    if node.is_indirect:
        if node.objgen in seen:
            return
        seen.add(node.objgen)
    nums = node.get("/Nums")
    if isinstance(nums, Array):
        keys.extend(int(nums[i]) for i in range(0, len(nums) - 1, 2) if _is_number(nums[i]))
    kids_of = node.get("/Kids")
    for kid in (kids_of if isinstance(kids_of, Array) else []):
        _number_tree_keys(kid, keys, seen, depth + 1)


def _rightmost_leaf(tree: Dictionary) -> tuple[Dictionary, list] | None:
    """The leaf of a number tree that holds its largest keys, and the nodes above it (None if broken)."""
    node, path = tree, []
    while not isinstance(node.get("/Nums"), Array) and isinstance(node.get("/Kids"), Array) and len(node.Kids):
        path.append(node)
        node = node.Kids[len(node.Kids) - 1]
        if not isinstance(node, Dictionary) or len(path) > 32:
            return None
    return node, path


def _number_tree_append(tree: Dictionary, key: int, value) -> None:
    """Add an entry whose key is larger than every key in the tree (to the rightmost leaf)."""
    node, path = _rightmost_leaf(tree)
    nums = node.get("/Nums")
    if not isinstance(nums, Array):
        nums = Array()
        node["/Nums"] = nums
    nums.append(key)
    nums.append(value)
    for holder in path[1:] + [node]:                  # the root of a number tree has no /Limits
        limits = holder.get("/Limits")
        if isinstance(limits, Array) and len(limits) == 2:
            holder["/Limits"] = Array([limits[0], key])


def _existing_owners(pdf: pikepdf.Pdf, page: pikepdf.Page) -> Array | None:
    key = page.obj.get("/StructParents")
    if key is None:
        return None
    try:
        slot = _parent_tree_slot(pdf, int(key))
    except (TypeError, ValueError):
        return None
    if slot is None:
        return None
    value = slot[0][slot[1]]
    return value if isinstance(value, Array) else None


def _owners_array(pdf: pikepdf.Pdf, root: Dictionary, page: pikepdf.Page) -> Array | None:
    """The parent tree array of a page, made if the page has none yet (None if it is broken)."""
    key = page.obj.get("/StructParents")
    if key is not None:
        try:
            slot = _parent_tree_slot(pdf, int(key))
        except (TypeError, ValueError):
            slot = None
        if slot is not None:
            value = slot[0][slot[1]]
            return value if isinstance(value, Array) else None
    tree = root.get("/ParentTree")
    if not isinstance(tree, Dictionary) or _rightmost_leaf(tree) is None:
        return None
    keys: list[int] = []
    _number_tree_keys(tree, keys, set())
    next_key = root.get("/ParentTreeNextKey")
    new_key = max(max(keys) + 1 if keys else 0, int(next_key) if _is_number(next_key) else 0)
    array = pdf.make_indirect(Array())
    _number_tree_append(tree, new_key, array)
    page.obj["/StructParents"] = new_key
    root["/ParentTreeNextKey"] = new_key + 1
    return array


class _Tree:
    """The existing tag tree: which elements are in it, in which order, and where new ones go."""

    def __init__(self, pdf: pikepdf.Pdf, root: Dictionary) -> None:
        self.root = root
        self.roles = Roles(pdf)
        self.order: dict[tuple, int] = {}
        self.chain_end: dict[tuple, Dictionary] = {}
        stack = list(reversed(kids(root)))
        while stack:
            node = stack.pop()
            if not is_element(node) or not node.is_indirect or node.objgen in self.order:
                continue
            self.order[node.objgen] = len(self.order)
            stack.extend(reversed(kids(node)))

    def reachable(self, element) -> bool:
        return is_element(element) and element.is_indirect and element.objgen in self.order

    def add(self, element: Dictionary) -> None:
        stack = [element]
        while stack:
            node = stack.pop()
            if is_element(node) and node.is_indirect and node.objgen not in self.order:
                self.order[node.objgen] = len(self.order)
                stack.extend(kids(node))

    def top(self) -> Dictionary:
        """The element new content goes into when nothing else is known (Document)."""
        for kid in kids(self.root):
            if is_element(kid) and self.roles.of(kid) in _GROUPING:
                return kid
        return self.root

    def anchor(self, owned: tuple | None) -> tuple[Dictionary, object] | None:
        """
        (container, reference) for content read right after the owner's content: a grouping
        element (Document, Sect, Div, ...) that directly owns the MCID gets the new element
        next to that MCID; otherwise the new element goes next to the owner's ancestor that is
        a child of the nearest grouping element (never inside a paragraph, list or table).
        """
        if owned is None or not self.reachable(owned[0]):
            return None
        node, reference, steps = owned[0], ("mcid", owned[1]), 0
        while is_element(node) and steps < 200:
            if self.roles.of(node) in _GROUPING:
                return node, reference
            reference, node, steps = node, node.get("/P"), steps + 1
        if isinstance(node, Dictionary) and node.is_indirect and node.objgen == self.root.objgen:
            return node, reference
        return None

    @staticmethod
    def _key(container: Dictionary, reference) -> tuple:
        if isinstance(reference, tuple):
            return (container.objgen,) + reference
        return ("element", reference.objgen)

    @staticmethod
    def _find(items: list, reference) -> int | None:
        if not isinstance(reference, tuple):
            return _position(items, reference)
        if reference[0] == "mcid":
            for position, item in enumerate(items):
                if isinstance(item, Dictionary):
                    if item.get("/Type") == Name.MCR and _is_number(item.get("/MCID")) \
                            and int(item.MCID) == reference[1]:
                        return position
                elif _is_number(item) and int(item) == reference[1]:
                    return position
        return None

    def insert_after(self, container: Dictionary, reference, element: Dictionary) -> None:
        """After the reference, and after the elements already put there (they come first)."""
        key = self._key(container, reference)
        items = kids(container)
        last = self.chain_end.get(key)
        position = _position(items, last) if last is not None else None
        if position is None:
            position = self._find(items, reference)
        position = len(items) if position is None else position + 1
        items.insert(position, element)
        set_kids(container, items)
        element["/P"] = container
        self.chain_end[key] = element

    def insert_before(self, container: Dictionary, reference, element: Dictionary) -> None:
        items = kids(container)
        position = self._find(items, reference)
        items.insert(len(items) if position is None else position, element)
        set_kids(container, items)
        element["/P"] = container


# --- reading a page -----------------------------------------------------------------------

def _mcid(operands, holder) -> int | None:
    if len(operands) < 2:
        return None
    properties = operands[1]
    if isinstance(properties, Name):
        resources = holder.get("/Resources")
        named = resources.get("/Properties") if isinstance(resources, Dictionary) else None
        properties = named.get(str(properties)) if isinstance(named, Dictionary) else None
    value = properties.get("/MCID") if isinstance(properties, Dictionary) else None
    return int(value) if _is_number(value) else None


def _form_content(form, depth: int = 0, seen: set | None = None) -> tuple[bool, bool, bool]:
    """(shows text, paints pictures, has marked content) of a form XObject and the forms in it."""
    seen = set() if seen is None else seen
    if form.objgen in seen or depth > 8:
        return False, False, True                          # a loop: treat as marked (left alone)
    seen.add(form.objgen)
    text = pictures = marked = False
    try:
        operations = pikepdf.parse_content_stream(form)
    except Exception:
        return False, False, True
    resources = form.get("/Resources")
    xobjects = resources.get("/XObject") if isinstance(resources, Dictionary) else None
    for operands, operator in operations:
        name = str(operator)
        if name in _SHOW:
            text = True
        elif name in ("BMC", "BDC"):
            marked = True
        elif name == "INLINE IMAGE":
            pictures = True
        elif name == "Do" and isinstance(xobjects, Dictionary):
            inner = xobjects.get(str(operands[0]))
            if isinstance(inner, pikepdf.Stream) and inner.get("/Subtype") == Name.Image:
                pictures = True
            elif isinstance(inner, pikepdf.Stream):
                t, p, m = _form_content(inner, depth + 1, seen)
                text, pictures, marked = text or t, pictures or p, marked or m
    return text, pictures, marked


def _blank(operands, name: str, widths: _Widths) -> bool:
    """Whether a text operator shows only spaces (one-byte fonts; two-byte codes are not decoded)."""
    if widths.two_byte:
        return False
    strings = [operand for operand in (operands[0] if name == "TJ" and operands else operands[-1:])
               if isinstance(operand, (pikepdf.String, bytes))]
    return all(not bytes(text).strip(b" \t\r\n\x00") for text in strings)


@dataclass
class _Shown:
    """Where a text operator draws: start and end of its text on the page, size, spaces only."""
    origin: fitz.Point
    end: fitz.Point
    size: float
    blank: bool


def _geometry(operations: list, holder: Dictionary, to_page: fitz.Matrix) -> tuple[dict[int, _Shown], dict[int, fitz.Matrix]]:
    """
    Follow the graphics and text state (as marking.py does): where each text operator draws,
    and the transformation matrix at each picture or form.
    """
    resources = holder.get("/Resources")
    fonts = resources.get("/Font") if isinstance(resources, Dictionary) else None
    widths_cache: dict[str, _Widths] = {}
    texts: dict[int, _Shown] = {}
    placements: dict[int, fitz.Matrix] = {}
    state = _State()
    stack: list[_State] = []
    text_matrix = line_matrix = fitz.Identity
    for index, (operands, operator) in enumerate(operations):
        name = str(operator)
        try:
            if name == "q":
                stack.append(_State(fitz.Matrix(state.ctm), state.font, state.size, state.char_spacing,
                                    state.word_spacing, state.scale, state.leading, state.rise))
            elif name == "Q":
                if stack:
                    state = stack.pop()
            elif name == "cm":
                state.ctm = _matrix(operands) * state.ctm
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
            elif name in ("Do", "INLINE IMAGE"):
                placements[index] = fitz.Matrix(state.ctm)
        except (TypeError, ValueError, IndexError):
            continue
        if name not in _SHOW:
            continue
        if name in ("'", '"'):
            line_matrix = fitz.Matrix(1, 0, 0, 1, 0, -state.leading) * line_matrix
            text_matrix = fitz.Matrix(line_matrix)
            if name == '"' and len(operands) >= 2:
                state.word_spacing, state.char_spacing = float(operands[0]), float(operands[1])
        widths = state.font or _Widths(None)
        origin = fitz.Point(0, state.rise) * text_matrix * state.ctm * to_page
        full = text_matrix * state.ctm
        size = abs(state.size) * abs(full.a * full.d - full.b * full.c) ** 0.5 or 10.0
        shown = 0.0
        for operand in ((operands[0] if operands else []) if name == "TJ" else operands[-1:]):
            if isinstance(operand, (pikepdf.String, bytes)):
                for code in widths.codes(bytes(operand)):
                    shown += (widths.width(code) / 1000.0 * state.size + state.char_spacing
                              + (state.word_spacing if code == 32 and not widths.two_byte else 0.0)) * state.scale
            else:
                try:                                      # a TJ number moves the next glyph back
                    shown -= float(operand) / 1000.0 * state.size * state.scale
                except (TypeError, ValueError):
                    pass
        text_matrix = fitz.Matrix(1, 0, 0, 1, shown, 0) * text_matrix
        end = fitz.Point(0, state.rise) * text_matrix * state.ctm * to_page
        texts[index] = _Shown(origin, end, size, _blank(operands, name, widths))
    return texts, placements


def _next_to(before: _Shown, after: _Shown) -> bool:
    """The same line, right after the text before (e.g. text drawn letter by letter; superscripts and
    letters drawn a little lower count, the next line does not: lines are at least a size apart)."""
    return abs(after.origin.y - before.origin.y) < max(2.0, before.size * 0.9) \
        and -before.size < after.origin.x - before.end.x < max(4.0, before.size * 2.5)


def _plan_page(page: pikepdf.Page, index: int, fitz_page: fitz.Page, items: list[Item], owners: Array | None,
               tree: _Tree) -> _PagePlan:
    """Find the content of a page that no tag reaches and rewrite the page with marks around it."""
    plan = _PagePlan(index)
    operations = list(pikepdf.parse_content_stream(page))
    used = [m for operands, operator in operations if str(operator) == "BDC"
            for m in [_mcid(operands, page.obj)] if m is not None]
    next_mcid = max(used + [len(owners) - 1 if owners is not None else -1]) + 1
    resources = page.obj.get("/Resources")
    xobjects = resources.get("/XObject") if isinstance(resources, Dictionary) else None
    to_page = fitz_page.transformation_matrix
    texts, placements = _geometry(operations, page.obj, to_page)

    def owner_of(mcid: int):
        if owners is None or not 0 <= mcid < len(owners):
            return None
        owner = owners[mcid]
        return owner if is_element(owner) else None

    def layout_target(point: fitz.Point):
        hits = [i for i, item in enumerate(items) if item.kind not in _NOT_TEXT and item.contains(point)]
        content = [i for i in hits if items[i].kind != "Artifact"]
        if content:
            return content[0]
        return _ARTIFACT if hits else None

    # A header, footer or page number is decided per line: when a line is drawn letter by letter
    # the layout may take single letters for a repeated footer; if any part of a line is
    # content, the whole line is content (text is never hidden on a guess).
    keep_as_content: set[int] = set()
    marks_seen: list[bool] = []
    line: list[int] = []
    claimed_count, line_count = 0, -1

    def finish_line() -> None:
        kinds = [layout_target(texts[i].origin) == _ARTIFACT for i in line]
        if any(kinds) and not all(kinds):
            keep_as_content.update(i for i, artifact in zip(line, kinds) if artifact)
        line.clear()

    for position, (operands, operator) in enumerate(operations):
        name = str(operator)
        if name in ("BMC", "BDC"):
            claimed = (bool(operands) and str(operands[0]) == "/Artifact") or \
                (name == "BDC" and _mcid(operands, page.obj) is not None)
            claimed_count += claimed
            marks_seen.append(claimed or (bool(marks_seen) and marks_seen[-1]))
        elif name == "EMC":
            if marks_seen:
                marks_seen.pop()
        elif position in texts and not texts[position].blank and not (marks_seen and marks_seen[-1]):
            if line and (claimed_count != line_count or not _next_to(texts[line[-1]], texts[position])):
                finish_line()
            line.append(position)
            line_count = claimed_count
    finish_line()

    marks: list[tuple[str, int | None]] = []        # (tag, MCID) of the open marked-content sequences
    out: list[tuple] = []
    changed = False
    open_kind: object = None                        # None, _ARTIFACT, or the _Plan being marked
    current: _Plan | None = None                    # the element untagged text is added to
    current_key: object = None                      # the layout item it came from
    current_shown: _Shown | None = None             # its last piece of text
    last_owner: tuple | None = None                 # (owner, MCID) of the tagged content drawn last
    list_id: int | None = None
    lists = 0
    # an open sequence whose MCID no element of the tree owns: [MCID, depth, text, pictures, owner, nested marks]
    dangling: list | None = None

    def forget_text() -> None:
        nonlocal current, current_key, current_shown
        current, current_key, current_shown = None, None, None

    def close() -> None:
        nonlocal open_kind
        if open_kind is not None:
            out.append(([], Operator("EMC")))
            open_kind = None

    def new_plan(tag: str, level: int = 0) -> _Plan:
        nonlocal list_id, lists
        if tag == "LI":
            if list_id is None:
                lists += 1
                list_id = lists
        else:
            list_id = None
        made = _Plan(tag, level, after=last_owner, list_id=list_id if tag == "LI" else None)
        plan.plans.append(made)
        return made

    def mark(target: _Plan) -> None:
        nonlocal open_kind, next_mcid, changed
        if open_kind is target:
            return
        close()
        tag = {"LI": "LBody", "H": f"H{target.level}" if 1 <= target.level <= 6 else "H"}.get(target.tag, target.tag)
        out.append(([Name("/" + tag), Dictionary(MCID=next_mcid)], Operator("BDC")))
        target.mcids.append(next_mcid)
        next_mcid += 1
        open_kind = target
        changed = True

    def mark_artifact() -> None:
        nonlocal open_kind, changed
        if open_kind == _ARTIFACT:
            return
        close()
        out.append(([Name.Artifact], Operator("BMC")))
        open_kind = _ARTIFACT
        plan.artifacts += 1
        changed = True

    def text_plan(shown: _Shown, content_only: bool = False):
        nonlocal current, current_key, current_shown
        target = layout_target(shown.origin)
        if target == _ARTIFACT:
            if not content_only:
                return _ARTIFACT
            target = None
        next_to = current_shown is not None and _next_to(current_shown, shown)
        if target is None:                                  # text the layout did not see: a paragraph
            key, tag, level = ("loose", len(plan.plans)), "P", 0
        else:
            item = items[target]
            key = target
            tag = {"H": "H", "LI": "LI", "Caption": "Caption"}.get(item.kind, "P")
            level = item.level if item.kind == "H" else 0
        if current is not None and (key == current_key or (next_to and (target is None or
                                                                        (current.tag, current.level) == (tag, level)))):
            current_shown = shown
            return current
        current = new_plan(tag, level)
        current.order = target if isinstance(target, int) else None
        current_key, current_shown = key, shown
        return current

    def picture_plan(rect: fitz.Rect):
        if is_decoration(rect, fitz_page.rect):
            return _ARTIFACT
        overlap = {i: abs(item.rect & rect) for i, item in enumerate(items) if item.kind in ("Figure", "Decoration")}
        best = max(overlap, key=overlap.get) if overlap and max(overlap.values()) > 0 else None
        if best is not None and items[best].kind == "Decoration":
            return _ARTIFACT                                  # a logo repeated in the margins
        forget_text()
        made = new_plan("Figure")
        made.order = best
        return made

    def placement(matrix: fitz.Matrix, box=(0.0, 0.0, 1.0, 1.0)) -> fitz.Rect:
        x0, y0, x1, y1 = box
        corners = [fitz.Point(x, y) * matrix * to_page for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
        return fitz.Rect(min(p.x for p in corners), min(p.y for p in corners),
                         max(p.x for p in corners), max(p.y for p in corners))

    def untagged() -> bool:
        return not any(tag == "/Artifact" or mcid is not None for tag, mcid in marks)

    def tagged_seen(owner, mcid: int) -> None:
        nonlocal last_owner, list_id
        if plan.first_owner is None:
            plan.first_owner = (owner, mcid)
        plan.owners.append((owner, mcid))
        last_owner = (owner, mcid)
        list_id = None
        forget_text()

    for position, (operands, operator) in enumerate(operations):
        name = str(operator)
        if name in _CLOSE_BEFORE:
            close()

        if name in ("BMC", "BDC"):
            mcid = _mcid(operands, page.obj) if name == "BDC" else None
            outer_free = untagged()
            if dangling is not None:
                dangling[5] = True                          # marks inside: leave it as it is
            marks.append((str(operands[0]) if operands else "", mcid))
            if mcid is not None and outer_free:
                owner = owner_of(mcid)
                if owner is not None and tree.reachable(owner):
                    tagged_seen(owner, mcid)
                elif str(operands[0]) != "/Artifact":
                    dangling = [mcid, len(marks), False, False, owner, False]
        elif name == "EMC":
            if dangling is not None and len(marks) == dangling[1]:
                mcid, _, has_text, has_pictures, owner, nested = dangling
                if nested:
                    pass
                elif owner is not None:                    # an element outside the tree
                    plan.plans.append(_Plan("", after=last_owner, existing=owner, mcids=[mcid]))
                    forget_text()
                elif has_text or has_pictures:             # an MCID nobody owns
                    made = new_plan("P" if has_text else "Figure")
                    made.mcids.append(mcid)
                    forget_text()
                dangling = None
            if marks:
                marks.pop()

        if position in texts:
            shown = texts[position]
            if dangling is not None:
                dangling[2] = True
            elif untagged():
                if shown.blank:
                    # a space on its own goes with the text it follows; alone it is no content
                    target = current if current is not None else _ARTIFACT
                else:
                    target = text_plan(shown, content_only=position in keep_as_content)
                if target == _ARTIFACT:
                    mark_artifact()
                else:
                    mark(target)
            out.append((operands, operator))
            continue

        if name in ("Do", "INLINE IMAGE"):
            xobject = xobjects.get(str(operands[0])) if name == "Do" and isinstance(xobjects, Dictionary) else None
            is_picture = name == "INLINE IMAGE" or (isinstance(xobject, pikepdf.Stream)
                                                    and xobject.get("/Subtype") == Name.Image)
            if dangling is not None:
                if is_picture:
                    dangling[3] = True
                elif isinstance(xobject, pikepdf.Stream):
                    form_text, form_pictures, form_marked = _form_content(xobject)
                    dangling[2] = dangling[2] or form_text
                    dangling[3] = dangling[3] or form_pictures
                    dangling[5] = dangling[5] or form_marked
            elif untagged():
                close()
                target = None
                ctm = placements.get(position, fitz.Identity)
                if is_picture:
                    target = picture_plan(placement(ctm))
                elif isinstance(xobject, pikepdf.Stream) and xobject.get("/Subtype") == Name.Form:
                    form_text, form_pictures, form_marked = _form_content(xobject)
                    if not form_marked and (form_text or form_pictures):
                        box = [float(v) for v in xobject.get("/BBox", [0, 0, 1, 1])]
                        rect = placement(_matrix(xobject.get("/Matrix", [1, 0, 0, 1, 0, 0])) * ctm, box)
                        if form_text:                      # a form is a piece of its own, never decoration
                            middle = fitz.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
                            target = text_plan(_Shown(middle, middle, 10.0, False), content_only=True)
                            forget_text()
                        else:
                            target = picture_plan(rect)
                if target == _ARTIFACT:
                    mark_artifact()
                elif target is not None:
                    mark(target)
                out.append((operands, operator))
                close()
                continue
        out.append((operands, operator))
    close()
    if changed:
        plan.new_contents = pikepdf.unparse_content_stream(out)
    return plan


# --- building the new elements ------------------------------------------------------------

def _make(pdf: pikepdf.Pdf, tag: str, page: Dictionary, mcids: list[int] | None = None) -> Dictionary:
    element = pdf.make_indirect(Dictionary(Type=Name.StructElem, S=Name("/" + tag), Pg=page))
    if mcids:
        element["/K"] = Array(mcids)
    return element


def _place(tree: _Tree, plan: _Plan, page_plan: _PagePlan, fallback, element: Dictionary) -> None:
    """Put a new element where it is read (see the module description)."""
    anchor = tree.anchor(plan.after)
    if anchor is not None:
        tree.insert_after(*anchor, element)
        return
    first = tree.anchor(page_plan.first_owner)
    if first is not None:
        tree.insert_before(*first, element)
        return
    if fallback is not None:
        tree.insert_after(*fallback, element)
        return
    tree.insert_after(tree.top(), ("end",), element)


def _fallback_anchor(tree: _Tree, owners_by_page: dict[int, list], index: int):
    """For a page without tagged content: after the last tagged content of the pages before."""
    for previous in range(index - 1, -1, -1):
        candidates = [owned for owned in owners_by_page.get(previous, []) if tree.reachable(owned[0])]
        if candidates:
            anchor = tree.anchor(max(candidates, key=lambda owned: tree.order[owned[0].objgen]))
            if anchor is not None:
                return anchor
    return None


def _in_reading_order(plans: list[_Plan]) -> list[_Plan]:
    """
    New elements that follow the same tagged content (nothing tagged is drawn between them) are
    read in the page's layout order (top to bottom, column by column), like a file tagged anew;
    pieces the layout does not know stay right after the piece drawn before them.
    """
    result: list[_Plan] = []
    run: list[_Plan] = []

    def flush() -> None:
        keyed, base, sub = [], -1, 0
        for position, plan in enumerate(run):
            if plan.order is not None:
                base, sub = plan.order, 0
            else:
                sub += 1
            keyed.append(((base, sub, position), plan))
        result.extend(plan for _, plan in sorted(keyed, key=lambda entry: entry[0]))
        run.clear()

    for plan in plans:
        if run and plan.after is not run[-1].after:
            flush()
        run.append(plan)
    flush()
    return result


def _build(pdf: pikepdf.Pdf, tree: _Tree, page: pikepdf.Page, page_plan: _PagePlan, owners: Array, fallback,
           result: LeftoverResult, headings: list) -> None:
    lists: dict[int, Dictionary] = {}
    for plan in _in_reading_order(page_plan.plans):
        if plan.existing is not None:                       # an element outside the tree
            top, steps = plan.existing, 0
            while is_element(top.get("/P")) and not tree.reachable(top.get("/P")) and steps < 50:
                top, steps = top.get("/P"), steps + 1
            if not top.is_indirect or tree.reachable(top):
                continue                                    # linked already (it owns more MCIDs)
            _place(tree, plan, page_plan, fallback, top)
            tree.add(top)
            result.linked += 1
            continue
        if not plan.mcids:
            continue
        if plan.tag == "LI":
            owner = _make(pdf, "LBody", page.obj, plan.mcids)
            item = _make(pdf, "LI", page.obj)
            item["/K"] = Array([owner])
            owner["/P"] = item
            group = lists.get(plan.list_id)
            if group is None:
                group = _make(pdf, "L", page.obj)
                group["/K"] = Array()
                _place(tree, plan, page_plan, fallback, group)
                lists[plan.list_id] = group
                result.elements["L"] += 1
            group.K.append(item)
            item["/P"] = group
            result.elements["LI"] += 1
        else:
            tag = f"H{max(1, min(6, plan.level or 1))}" if plan.tag == "H" else plan.tag
            owner = _make(pdf, tag, page.obj, plan.mcids)
            _place(tree, plan, page_plan, fallback, owner)
            if plan.tag == "H":
                headings.append((owner, max(1, min(6, plan.level or 1))))
            else:
                result.elements[tag] += 1
        tree.add(owner)
        for mcid in plan.mcids:
            while len(owners) <= mcid:
                owners.append(None)
            owners[mcid] = owner


def _fix_heading_levels(tree: _Tree, new_headings: list, result: LeftoverResult) -> None:
    """
    New headings keep the level the layout gave them as far as the headings around them allow:
    at most one level below the heading before them, and high enough that the next old heading
    does not skip a level. A document that uses plain H gets plain H. If no level fits, the
    heading becomes a paragraph.
    """
    if not new_headings:
        return
    wanted = {element.objgen: level for element, level in new_headings}
    sequence = []                                           # (element, level, new) in reading order
    plain = False
    stack, seen = list(reversed(kids(tree.root))), set()
    while stack:
        node = stack.pop()
        if not is_element(node) or not node.is_indirect or node.objgen in seen:
            continue
        seen.add(node.objgen)
        role = tree.roles.of(node)
        if node.objgen in wanted:
            sequence.append((node, wanted[node.objgen], True))
        elif role == "H":
            plain = True
        elif role in _HEADINGS:
            sequence.append((node, int(role[1]), False))
        stack.extend(reversed(kids(node)))
    previous = 0
    for position, (element, level, new) in enumerate(sequence):
        if not new:
            previous = level
            continue
        if plain:
            element["/S"] = Name.H
            result.elements["H"] += 1
            continue
        following = next((later for _, later, is_new in sequence[position + 1:] if not is_new), None)
        low, high = max(1, following - 1 if following else 1), previous + 1
        if low > high:
            element["/S"] = Name.P
            result.elements["P"] += 1
            continue
        level = max(low, min(level, high))
        element["/S"] = Name(f"/H{level}")
        result.elements[f"H{level}"] += 1
        previous = level


# --- the whole document -------------------------------------------------------------------

def _needs_work(pdf: pikepdf.Pdf, tree: _Tree) -> bool:
    """A quick look: does any page show text or pictures that no tag reaches?"""
    forms: dict[tuple, bool] = {}

    def shows_content(page, operands) -> bool:
        resources = page.obj.get("/Resources")
        xobjects = resources.get("/XObject") if isinstance(resources, Dictionary) else None
        xobject = xobjects.get(str(operands[0])) if isinstance(xobjects, Dictionary) and operands else None
        if not isinstance(xobject, pikepdf.Stream):
            return False
        if xobject.get("/Subtype") == Name.Image:
            return True
        if xobject.objgen not in forms:
            text, pictures, marked = _form_content(xobject)
            forms[xobject.objgen] = (text or pictures) and not marked
        return forms[xobject.objgen]

    for page in pdf.pages:
        owners = _existing_owners(pdf, page)
        claimed: list[bool] = []
        try:
            operations = pikepdf.parse_content_stream(page)
        except Exception:
            continue
        for operands, operator in operations:
            name = str(operator)
            if name in ("BMC", "BDC"):
                tag = str(operands[0]) if operands else ""
                mcid = _mcid(operands, page.obj) if name == "BDC" else None
                if mcid is not None and not (isinstance(owners, Array) and mcid < len(owners)
                                             and tree.reachable(owners[mcid])) and tag != "/Artifact":
                    return True                             # an MCID no element in the tree owns
                claimed.append(tag == "/Artifact" or mcid is not None or (bool(claimed) and claimed[-1]))
            elif name == "EMC":
                if claimed:
                    claimed.pop()
            elif name in _SHOW or name in ("Do", "INLINE IMAGE"):
                if (not claimed or not claimed[-1]) and (name != "Do" or shows_content(page, operands)):
                    return True
    return False


def tag_leftovers(pdf: pikepdf.Pdf, force: bool = False) -> LeftoverResult:
    """
    Tag the content of a partly tagged file that no tag reaches (see the module description).
    Done once per opened file (unless force); a file without a tag tree is left alone.
    """
    result = LeftoverResult()
    if not force and getattr(pdf, _DONE_ATTRIBUTE, False):
        return result
    try:
        setattr(pdf, _DONE_ATTRIBUTE, True)
    except AttributeError:
        pass
    root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(root, Dictionary) or root.get("/K") is None or not isinstance(root.get("/ParentTree"), Dictionary):
        result.skipped["no usable tag tree"] += 1
        return result
    tree = _Tree(pdf, root)
    if not tree.order or not _needs_work(pdf, tree):
        return result

    from pdfaccessguru.pipeline.transaction import _glyphs

    before = io.BytesIO()
    pdf.save(before)
    page_plans: dict[int, _PagePlan] = {}
    owners_by_page: dict[int, list] = {}
    originals: dict[int, object] = {}
    with fitz.open(stream=before.getvalue(), filetype="pdf") as layout_document:
        pages_items = analyse(layout_document)
        for index, page in enumerate(pdf.pages):
            try:
                page_plan = _plan_page(page, index, layout_document[index], pages_items[index],
                                       _existing_owners(pdf, page), tree)
            except Exception:
                result.skipped["page could not be read"] += 1
                continue
            owners_by_page[index] = page_plan.owners
            if page_plan.new_contents is not None or page_plan.plans:
                page_plans[index] = page_plan

        # The parent tree entries first (made for pages without one), before anything else changes.
        arrays: dict[int, Array] = {}
        for index in sorted(page_plans):
            try:
                owners = _owners_array(pdf, root, pdf.pages[index])
            except Exception:
                owners = None
            if owners is None:                              # a broken parent tree entry: leave the page
                del page_plans[index]
                result.skipped["broken parent tree entry"] += 1
            else:
                arrays[index] = owners

        # Marks must not change what a page shows: compare text and character positions.
        for index, page_plan in page_plans.items():
            if page_plan.new_contents is not None:
                page = pdf.pages[index]
                originals[index] = page.obj.get("/Contents")
                page.obj["/Contents"] = pdf.make_stream(page_plan.new_contents)
        if originals:
            after = io.BytesIO()
            pdf.save(after)
            with fitz.open(stream=after.getvalue(), filetype="pdf") as marked:
                for index in list(originals):
                    old, new = layout_document[index], marked[index]
                    if old.get_text() != new.get_text() or _glyphs(old) != _glyphs(new):
                        pdf.pages[index].obj["/Contents"] = originals.pop(index)
                        del page_plans[index]
                        result.skipped["the page would change"] += 1

    headings: list = []
    for index in sorted(page_plans):
        page_plan = page_plans[index]
        _build(pdf, tree, pdf.pages[index], page_plan, arrays[index], _fallback_anchor(tree, owners_by_page, index),
               result, headings)
        result.artifacts += page_plan.artifacts
        if page_plan.new_contents is not None:
            result.pages += 1
    _fix_heading_levels(tree, headings, result)
    if result.changed:
        mark_info = pdf.Root.get("/MarkInfo")
        if isinstance(mark_info, Dictionary):
            mark_info["/Marked"] = True
        else:
            pdf.Root["/MarkInfo"] = Dictionary(Marked=True)
    return result
