"""Reading and rebuilding the structure tree without losing content or reading order."""

from __future__ import annotations

from pikepdf import Array, Dictionary, Name, Pdf

# Standard structure types of PDF 1.7. A role map cannot change their meaning (rule 7.1-7).
STANDARD_TYPES = frozenset({
    "Document", "Part", "Art", "Sect", "Div", "BlockQuote", "Caption", "TOC", "TOCI", "Index",
    "NonStruct", "Private", "P", "H", "H1", "H2", "H3", "H4", "H5", "H6", "L", "LI", "Lbl",
    "LBody", "Table", "TR", "TH", "TD", "THead", "TBody", "TFoot", "Span", "Quote", "Note",
    "Reference", "BibEntry", "Code", "Link", "Annot", "Ruby", "RB", "RT", "RP", "Warichu",
    "WT", "WP", "Figure", "Formula", "Form",
})


def is_element(item) -> bool:
    """True for structure elements; False for marked content, object references and numbers."""
    return isinstance(item, Dictionary) and "/S" in item and item.get("/Type") in (None, Name("/StructElem"))


def kids(element) -> list:
    if not isinstance(element, Dictionary):
        return []
    value = element.get("/K")
    if value is None:
        return []
    return list(value) if isinstance(value, Array) else [value]


def set_kids(element: Dictionary, items: list) -> None:
    if items:
        element["/K"] = Array(items)
    elif "/K" in element:
        del element["/K"]


def same(first, second) -> bool:
    """True if both are the same indirect PDF object."""
    return (isinstance(first, Dictionary) and isinstance(second, Dictionary)
            and first.is_indirect and second.is_indirect and first.objgen == second.objgen)


def index_of(items: list, element) -> int | None:
    return next((i for i, item in enumerate(items) if same(item, element)), None)


class Roles:
    """Standard types of structure elements, after following the document's role map."""

    def __init__(self, pdf: Pdf):
        root = pdf.Root.get("/StructTreeRoot")
        role_map = root.get("/RoleMap") if isinstance(root, Dictionary) else None
        self._map = role_map if isinstance(role_map, Dictionary) else None

    def of(self, item) -> str | None:
        if not is_element(item):
            return None
        name = str(item.get("/S")).lstrip("/")
        seen = set()
        while self._map is not None and name not in STANDARD_TYPES and name not in seen:
            seen.add(name)
            target = self._map.get("/" + name)
            if target is None:
                break
            name = str(target).lstrip("/")
        return name

    def is_(self, item, *types: str) -> bool:
        return self.of(item) in types


def page_of(element) -> Dictionary | None:
    """The page that integer MCIDs of this element refer to (its own or an ancestor's /Pg)."""
    current, steps = element, 0
    while is_element(current) and steps < 200:
        page = current.get("/Pg")
        if isinstance(page, Dictionary):
            return page
        current, steps = current.get("/P"), steps + 1
    return None


def has_content(item) -> bool:
    """True if the item or anything below it shows content (or carries replacement text)."""
    if not is_element(item):
        return True                          # MCID, marked-content or object reference
    if any(key in item for key in ("/Alt", "/ActualText", "/E")):
        return True
    return any(has_content(kid) for kid in kids(item))


def new_element(pdf: Pdf, type_name: str, parent: Dictionary, like: Dictionary | None = None) -> Dictionary:
    """A new, empty structure element of a standard type under the given parent."""
    element = pdf.make_indirect(Dictionary({
        "/Type": Name("/StructElem"), "/S": Name("/" + type_name), "/P": parent,
    }))
    page = page_of(like if like is not None else parent)
    if page is not None:
        element["/Pg"] = page
    return element


def move(pdf: Pdf, items: list, old_owner: Dictionary, new_owner: Dictionary) -> list:
    """
    Prepare items taken from old_owner's kids for new_owner's kids: structure elements get
    their new parent; marked content and object references are re-registered in the parent
    tree, so screen readers still find their owner. Returns the items to put into /K.
    """
    moved = []
    for item in items:
        if is_element(item):
            item["/P"] = new_owner
            moved.append(item)
        elif isinstance(item, int):
            moved.append(_move_mcid(pdf, item, old_owner, new_owner))
        elif isinstance(item, Dictionary) and item.get("/Type") == Name("/MCR"):
            _move_marked_content_reference(pdf, item, old_owner, new_owner)
            moved.append(item)
        elif isinstance(item, Dictionary) and item.get("/Type") == Name("/OBJR"):
            target = item.get("/Obj")
            key = target.get("/StructParent") if isinstance(target, Dictionary) else None
            if key is not None:
                _set_parent_tree_value(pdf, int(key), new_owner)
            moved.append(item)
        else:
            moved.append(item)
    return moved


def _move_mcid(pdf: Pdf, mcid: int, old_owner: Dictionary, new_owner: Dictionary):
    page = page_of(old_owner)
    if page is None:
        return mcid
    _set_parent_tree_mcid(pdf, page.get("/StructParents"), mcid, new_owner)
    new_page = new_owner.get("/Pg")
    if new_page is None:
        new_owner["/Pg"] = page
        return mcid
    if same(new_page, page):
        return mcid
    return Dictionary({"/Type": Name("/MCR"), "/Pg": page, "/MCID": mcid})


def _move_marked_content_reference(pdf: Pdf, reference: Dictionary, old_owner: Dictionary, new_owner: Dictionary) -> None:
    stream = reference.get("/Stm")
    page = reference.get("/Pg") or page_of(old_owner)
    if isinstance(page, Dictionary) and "/Pg" not in reference:
        reference["/Pg"] = page
    holder = stream if isinstance(stream, Dictionary) else page
    if isinstance(holder, Dictionary) and reference.get("/MCID") is not None:
        _set_parent_tree_mcid(pdf, holder.get("/StructParents"), int(reference["/MCID"]), new_owner)


def _parent_tree_slot(pdf: Pdf, key: int):
    """(Nums array, index of the value) of a parent tree entry, or None."""
    root = pdf.Root.get("/StructTreeRoot")
    tree = root.get("/ParentTree") if isinstance(root, Dictionary) else None
    stack, visited = [tree], set()
    while stack:
        node = stack.pop()
        if not isinstance(node, Dictionary):
            continue
        if node.is_indirect:
            if node.objgen in visited:
                continue
            visited.add(node.objgen)
        limits = node.get("/Limits")
        if isinstance(limits, Array) and len(limits) == 2 and not int(limits[0]) <= key <= int(limits[1]):
            continue
        nums = node.get("/Nums")
        if isinstance(nums, Array):
            for index in range(0, len(nums) - 1, 2):
                if int(nums[index]) == key:
                    return nums, index + 1
        stack.extend(node.get("/Kids") or [])
    return None


def _set_parent_tree_mcid(pdf: Pdf, key, mcid: int, owner: Dictionary) -> None:
    if key is None:
        return
    slot = _parent_tree_slot(pdf, int(key))
    if slot is None:
        return
    nums, index = slot
    owners = nums[index]
    if isinstance(owners, Array) and 0 <= mcid < len(owners):
        owners[mcid] = owner


def _set_parent_tree_value(pdf: Pdf, key: int, owner: Dictionary) -> None:
    slot = _parent_tree_slot(pdf, key)
    if slot is not None:
        nums, index = slot
        nums[index] = owner


def parent_tree_owner(pdf: Pdf, page: Dictionary, mcid: int):
    """The structure element that the parent tree names for an MCID on a page (for tests)."""
    key = page.get("/StructParents")
    slot = _parent_tree_slot(pdf, int(key)) if key is not None else None
    if slot is None:
        return None
    owners = slot[0][slot[1]]
    return owners[mcid] if isinstance(owners, Array) and 0 <= mcid < len(owners) else None
