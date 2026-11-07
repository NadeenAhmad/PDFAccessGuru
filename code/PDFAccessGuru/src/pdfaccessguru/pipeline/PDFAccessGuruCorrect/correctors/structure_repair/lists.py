"""
Lists. A list (L) holds list items (LI), nested lists and one caption; a list item holds a
label (Lbl, e.g. the bullet or number) and a body (LBody, the text).

Repairs keep each item whole: consecutive loose items become ONE list, a loose label and the
body after it become ONE item, and text that continues an item is added to that item.
"""

from __future__ import annotations

import re

from pikepdf import Dictionary, Name, Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.layout import Layout
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import (
    Roles, has_content, is_element, kids, move, new_element, set_kids,
)

LIST_PARTS = ("LI", "Lbl", "LBody")

# A bullet, dash or number at the start of a list item: "•", "–", "1.", "2)", "a)", "(iv)".
_MARKER = re.compile(r"^\s*(?:[•‣▪▫●○◦⁃∙·–—\-\*➢→►]"
                     r"|\(?(?:\d{1,3}|[a-zA-Z]|[ivxlcIVXLC]{1,5})[.)\]])(?:\s|$)")


def looks_like_marker(text: str) -> bool:
    return bool(_MARKER.match(text or ""))


class ListRepair:
    def __init__(self, pdf: Pdf):
        self.pdf = pdf
        self.roles = Roles(pdf)
        self._layout: Layout | None = None

    def _text(self, item, owner) -> str:
        if self._layout is None:
            self._layout = Layout(self.pdf)
        return self._layout.text(item, owner)

    def _child(self, item, kind: str):
        return next((kid for kid in kids(item) if self.roles.is_(kid, kind)), None)

    def _new_item(self, lst: Dictionary, parts: list, owner: Dictionary) -> Dictionary:
        item = new_element(self.pdf, "LI", lst, like=owner)
        set_kids(item, move(self.pdf, parts, owner, item))
        return item

    def _wrap(self, kind: str, parts: list, owner: Dictionary, parent: Dictionary) -> Dictionary:
        element = new_element(self.pdf, kind, parent, like=owner)
        set_kids(element, move(self.pdf, parts, owner, element))
        return element

    def _add_to_body(self, item: Dictionary, parts: list, owner: Dictionary) -> None:
        """Add content to the end of an item's body (creating the body if needed)."""
        body = self._child(item, "LBody")
        if body is None:
            body = self._wrap("LBody", parts, owner, item)
            set_kids(item, kids(item) + [body])
        else:
            set_kids(body, kids(body) + move(self.pdf, parts, owner, body))

    def _give_label(self, item: Dictionary, part, owner: Dictionary) -> None:
        """Make the part the label of the item (the item has no label yet)."""
        if is_element(part) and self.roles.is_(part, "Span", "Lbl"):
            if not self.roles.is_(part, "Lbl"):
                part["/S"] = Name("/Lbl")
            label = move(self.pdf, [part], owner, item)[0]
        else:
            label = self._wrap("Lbl", [part], owner, item)
        set_kids(item, [label] + kids(item))

    def repair_list(self, lst: Dictionary) -> bool:
        """Rebuild the children of a list so it holds only items, nested lists and a caption."""
        parts = kids(lst)
        has_items = any(self.roles.is_(part, "LI") for part in parts)
        result: list = []
        changed = False
        index = 0
        while index < len(parts):
            part = parts[index]
            kind = self.roles.of(part)
            following = parts[index + 1] if index + 1 < len(parts) else None
            previous = result[-1] if result else None
            index += 1
            if kind in ("LI", "L", "Caption"):
                result.append(part)
                continue
            changed = True
            if is_element(part) and not has_content(part):
                continue                                            # empty leftover tag
            next_item_lacks_label = self.roles.is_(following, "LI") and self._child(following, "Lbl") is None
            if kind == "Lbl":
                if self.roles.is_(following, "LBody"):
                    result.append(self._new_item(lst, [part, following], lst))
                    index += 1
                elif next_item_lacks_label:
                    self._give_label(following, part, lst)
                else:
                    result.append(self._new_item(lst, [part], lst))
                continue
            if kind == "LBody":
                if self.roles.is_(previous, "LI") and self._child(previous, "LBody") is None:
                    set_kids(previous, kids(previous) + move(self.pdf, [part], lst, previous))
                else:
                    result.append(self._new_item(lst, [part], lst))
                continue
            text = self._text(part, lst)
            short = len(text.strip()) <= 6
            short_marker = short and looks_like_marker(text)
            if next_item_lacks_label and (short_marker or (short and (kind == "Span" or not is_element(part)))):
                self._give_label(following, part, lst)               # e.g. a bullet tagged as Span
            elif short_marker and following is not None and self.roles.of(following) not in ("LI", "L", "Caption", "Lbl", "LBody"):
                label = self._wrap("Lbl", [part], lst, lst) if not is_element(part) else part
                if is_element(label) and not self.roles.is_(label, "Lbl"):
                    label["/S"] = Name("/Lbl")
                body = self._wrap("LBody", [following], lst, lst)
                result.append(self._new_item(lst, [label, body], lst))
                index += 1
            elif has_items and self.roles.is_(previous, "LI") and not looks_like_marker(text):
                self._add_to_body(previous, [part], lst)              # text that continues the item
            else:
                body = self._wrap("LBody", [part], lst, lst)
                result.append(self._new_item(lst, [body], lst))
        if changed:
            set_kids(lst, result)
        return changed

    def repair_parent(self, parent: Dictionary) -> bool:
        """Put loose list items, labels and bodies inside a parent into proper lists."""
        if self.roles.is_(parent, "L"):
            return self.repair_list(parent)
        parts = kids(parent)
        result: list = []
        changed = False
        index = 0
        while index < len(parts):
            if self.roles.of(parts[index]) not in LIST_PARTS:
                result.append(parts[index])
                index += 1
                continue
            end = index
            while end < len(parts) and self.roles.of(parts[end]) in LIST_PARTS:
                end += 1
            run = parts[index:end]
            previous = result[-1] if result else None
            if self.roles.is_(previous, "L"):
                # The list right before continues (e.g. after a page break), or its last
                # item is missing its body.
                set_kids(previous, kids(previous) + move(self.pdf, run, parent, previous))
                self.repair_list(previous)
            else:
                lst = new_element(self.pdf, "L", parent, like=parent)
                set_kids(lst, move(self.pdf, run, parent, lst))
                self.repair_list(lst)
                result.append(lst)
            changed = True
            index = end
        if changed:
            set_kids(parent, result)
        return changed

    def repair_item(self, item: Dictionary) -> bool:
        """Keep one label and one body in a list item; all other content joins the body."""
        parts = kids(item)
        label_at = next((i for i, part in enumerate(parts) if self.roles.is_(part, "Lbl")), None)
        body_at = next((i for i, part in enumerate(parts) if self.roles.is_(part, "LBody")), None)
        if label_at is not None and body_at is not None and label_at > body_at:
            label_at = None                                   # a "label" after the body is content
        if label_at is None:
            label_at = self._label_in_disguise(item, parts, body_at)
        keep = {label_at, body_at} - {None}
        if len(keep) == len(parts):
            return False
        body = parts[body_at] if body_at is not None else new_element(self.pdf, "LBody", item, like=item)
        before: list = []
        after: list = []
        for index, part in enumerate(parts):
            if index in keep or (is_element(part) and not has_content(part)):
                continue
            if self.roles.is_(part, "LBody"):                 # a second body: merge its content
                moved = move(self.pdf, kids(part), part, body)
            else:
                moved = move(self.pdf, [part], item, body)
            (before if body_at is not None and index < body_at else after).extend(moved)
        set_kids(body, before + (kids(body) if body_at is not None else []) + after)
        set_kids(item, ([parts[label_at]] if label_at is not None else []) + [body])
        return True

    def _label_in_disguise(self, item: Dictionary, parts: list, body_at: int | None) -> int | None:
        """
        The first content of an item without a label, if it is a bullet or number tagged as
        something else (e.g. a Span holding "•"). It is turned into the label in place.
        """
        first = next((i for i, part in enumerate(parts)
                      if i != body_at and not (is_element(part) and not has_content(part))), None)
        if first is None or (body_at is not None and first > body_at):
            return None
        part = parts[first]
        text = self._text(part, item).strip()
        is_span = self.roles.is_(part, "Span")
        if len(text) > 6 or not (looks_like_marker(text) or is_span or not is_element(part)):
            return None
        if is_span:
            part["/S"] = Name("/Lbl")
        else:
            parts[first] = self._wrap("Lbl", [part], item, item)
        return first

    def repair_all_loose_items(self) -> bool:
        """Find every list item, label or body outside its proper parent in the whole document."""
        root = self.pdf.Root.get("/StructTreeRoot")
        parents, stack, seen = [], list(kids(root)), set()
        while stack:
            element = stack.pop()
            if not is_element(element) or (element.is_indirect and element.objgen in seen):
                continue
            if element.is_indirect:
                seen.add(element.objgen)
            parts = kids(element)
            if not self.roles.is_(element, "L") and any(self.roles.of(part) in LIST_PARTS for part in parts) \
                    and not (self.roles.is_(element, "LI") and all(self.roles.of(p) in ("Lbl", "LBody") for p in parts
                                                                   if is_element(p))):
                parents.append(element)
            stack.extend(parts)
        changed = False
        for parent in parents:
            changed = self.repair_parent(parent) or changed
        return changed
