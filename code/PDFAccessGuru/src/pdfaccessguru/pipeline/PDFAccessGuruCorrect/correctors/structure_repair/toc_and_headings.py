"""
Tables of contents and headings.

- Consecutive loose TOC entries (TOCI) form ONE table of contents, or join the table of
  contents right next to them.
- A section with several unnumbered headings (H) is split into one section per heading, so
  every heading stays a heading and keeps its level (rule 7.4.4-1).
"""

from __future__ import annotations

from pikepdf import Dictionary, Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import (
    Roles, has_content, index_of, is_element, kids, move, new_element, set_kids,
)


def repair_toc_parent(pdf: Pdf, parent: Dictionary) -> bool:
    """Put loose TOC entries of a parent into a table of contents."""
    roles = Roles(pdf)
    if roles.is_(parent, "TOC"):
        return False
    parts = kids(parent)
    result: list = []
    changed = False
    index = 0
    while index < len(parts):
        if not roles.is_(parts[index], "TOCI"):
            result.append(parts[index])
            index += 1
            continue
        end = index
        while end < len(parts) and roles.is_(parts[end], "TOCI"):
            end += 1
        run = parts[index:end]
        following = parts[end] if end < len(parts) else None
        previous = result[-1] if result else None
        if roles.is_(previous, "TOC"):
            set_kids(previous, kids(previous) + move(pdf, run, parent, previous))
        elif roles.is_(following, "TOC"):
            set_kids(following, move(pdf, run, parent, following) + kids(following))
        else:
            toc = new_element(pdf, "TOC", parent, like=parent)
            set_kids(toc, move(pdf, run, parent, toc))
            result.append(toc)
        changed = True
        index = end
    if changed:
        set_kids(parent, result)
    return changed


def repair_toc(pdf: Pdf, toc: Dictionary) -> bool:
    """
    Keep only entries, nested tables of contents and a caption in a TOC. Other content (often
    the page number or a link that the tagging tool left outside the entry) joins the entry
    before it; content before the first entry gets an entry of its own.
    """
    roles = Roles(pdf)
    parts = kids(toc)
    result: list = []
    changed = False
    fresh_entry = None              # an entry created here, which following loose content joins
    for part in parts:
        if roles.of(part) in ("TOCI", "TOC", "Caption"):
            result.append(part)
            fresh_entry = None
            continue
        changed = True
        if is_element(part) and not has_content(part):
            continue
        previous = result[-1] if result else None
        starts_entry = roles.of(part) in ("Reference", "Link", "P", "Lbl") and fresh_entry is None
        if roles.is_(previous, "TOCI") and not starts_entry:
            set_kids(previous, kids(previous) + move(pdf, [part], toc, previous))
            continue
        entry = new_element(pdf, "TOCI", toc, like=toc)
        set_kids(entry, move(pdf, [part], toc, entry))
        result.append(entry)
        fresh_entry = entry
    if changed:
        set_kids(toc, result)
    return changed


# Grouping elements that can be split into two of the same kind without changing meaning.
_SPLITTABLE = ("Sect", "Div", "Art", "Part", "NonStruct")
# Entries that must not be copied to the new sibling (they describe or name the whole node).
_NOT_COPIED = ("/K", "/P", "/ID", "/T", "/Alt", "/ActualText", "/E", "/C", "/R")


def repair_headings(pdf: Pdf, node: Dictionary) -> bool:
    """Give each unnumbered heading (H) of a node its own section. Returns True if changed."""
    roles = Roles(pdf)
    parts = kids(node)
    starts = [i for i, part in enumerate(parts) if roles.is_(part, "H")]
    if len(starts) <= 1:
        return False
    groups = [parts[start:end] for start, end in zip(starts, starts[1:] + [len(parts)])]
    before = parts[:starts[0]]
    parent = node.get("/P")
    position = index_of(kids(parent), node) if is_element(parent) else None
    describes_whole_node = any(key in node for key in ("/Alt", "/ActualText", "/E"))

    if roles.of(node) in _SPLITTABLE and position is not None and not describes_whole_node:
        # Sect(H, P, H, P) -> Sect(H, P), Sect(H, P): the headings keep their level.
        siblings = []
        for group in groups[1:]:
            sibling = pdf.make_indirect(Dictionary({
                key: value for key, value in node.items() if key not in _NOT_COPIED
            }))
            sibling["/P"] = parent
            set_kids(sibling, move(pdf, group, node, sibling))
            siblings.append(sibling)
        set_kids(node, before + groups[0])
        parent_kids = kids(parent)
        set_kids(parent, parent_kids[:position + 1] + siblings + parent_kids[position + 1:])
        return True

    # Document(P, H, P, H, P) -> Document(P, Sect(H, P), Sect(H, P)): all headings move one
    # level down together, so their order and relative levels stay the same.
    sections = []
    for group in groups:
        section = new_element(pdf, "Sect", node, like=node)
        set_kids(section, move(pdf, group, node, section))
        sections.append(section)
    set_kids(node, before + sections)
    return True
