"""
Content that is marked as decoration (Artifact) and is at the same time referenced by a tag
(rule 7.1-2), e.g. "/Artifact <</MCID 3>> BDC ... EMC".

One of the two marks is wrong. The tag decides:
- the tag is named "Artifact" (some programs put decoration into the tag tree): the content stays
  decoration and the empty tag is removed;
- any other tag (P, Span, ...): the content becomes real content of that tag, because hiding real
  text from screen readers is worse than reading a header once too often.

Tagged content nested deeper inside a decoration block needs the page to be re-tagged (Phase 6)
and is left alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pikepdf
from pikepdf import Array, Dictionary, Name, Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import (
    _parent_tree_slot, is_element, kids, same, set_kids,
)

_ARTIFACT_ONLY_KEYS = ("/Type", "/Subtype", "/BBox", "/Attached")


@dataclass
class ArtifactResult:
    made_content: int = 0          # decoration that became real content
    kept_decoration: int = 0       # tags named "Artifact" removed, content stays decoration
    nested: int = 0                # tagged content deeper inside decoration (left alone)
    removed_tags: list[str] = field(default_factory=list)


def _owner(pdf: Pdf, page: Dictionary, mcid: int):
    key = page.get("/StructParents")
    slot = _parent_tree_slot(pdf, int(key)) if key is not None else None
    if slot is None:
        return None, None
    owners = slot[0][slot[1]]
    if isinstance(owners, Array) and 0 <= mcid < len(owners) and is_element(owners[mcid]):
        return owners[mcid], owners
    return None, owners


def _drop_reference(owner: Dictionary, page: Dictionary, mcid: int) -> None:
    """Remove the MCID from the tag's kids; remove the tag itself if nothing is left in it."""
    remaining = []
    for kid in kids(owner):
        if isinstance(kid, int) and kid == mcid:
            continue
        if isinstance(kid, Dictionary) and kid.get("/Type") == Name("/MCR") and kid.get("/MCID") == mcid \
                and (kid.get("/Pg") is None or same(kid.get("/Pg"), page)):
            continue
        remaining.append(kid)
    set_kids(owner, remaining)
    parent = owner.get("/P")
    if not remaining and isinstance(parent, Dictionary):
        set_kids(parent, [kid for kid in kids(parent) if not same(kid, owner)])


_PAINTING = {"Tj", "TJ", "'", '"', "S", "s", "f", "F", "f*", "B", "B*", "b", "b*", "sh", "Do", "BI", "EI"}


def _items(operations: list) -> list[tuple[list, bool]]:
    """Top-level items of a content slice: single operators, or whole marked-content sequences
    (with a flag telling whether tagged content (an MCID) is inside)."""
    items, depth, current, tagged = [], 0, [], False
    for operands, operator in operations:
        name = str(operator)
        if depth == 0 and name not in ("BMC", "BDC"):
            items.append(([(operands, operator)], False))
            continue
        if name in ("BMC", "BDC"):
            depth += 1
            props = operands[1] if len(operands) > 1 and isinstance(operands[1], Dictionary) else None
            tagged = tagged or (props is not None and props.get("/MCID") is not None)
        current.append((operands, operator))
        if name == "EMC":
            depth -= 1
            if depth == 0:
                items.append((current, tagged))
                current, tagged = [], False
    if current:
        items.append((current, tagged))
    return items


def _rewrap(inner: list, artifact_operands: list) -> list:
    """
    The content of a decoration block without its outer mark: tagged parts stay as they are,
    every other part that draws something is wrapped as decoration again. Text objects (BT/ET)
    are never split by a new mark.
    """
    out: list = []
    segment: list = []

    def flush() -> None:
        if any(str(operator) in _PAINTING or str(operator) in ("BMC", "BDC") for _, operator in segment):
            out.append((list(artifact_operands), pikepdf.Operator("BDC" if len(artifact_operands) > 1 else "BMC")))
            out.extend(segment)
            out.append(([], pikepdf.Operator("EMC")))
        else:
            out.extend(segment)
        segment.clear()

    for ops, tagged in _items(inner):
        name = str(ops[0][1])
        if tagged or name in ("BT", "ET"):
            flush()
            out.extend(ops)
        else:
            segment.extend(ops)
    flush()
    return out


def fix_tagged_artifacts(pdf: Pdf, page: pikepdf.Page) -> ArtifactResult:
    result = ArtifactResult()
    page_obj = page.obj
    operations = [list(item) for item in pikepdf.parse_content_stream(page)]
    rewrites: dict[int, tuple[int, list]] = {}       # start index -> (end index, new operators)
    stack: list[dict] = []
    changed = False
    for index, (operands, operator) in enumerate(operations):
        name = str(operator)
        if name in ("BMC", "BDC"):
            tag = str(operands[0])
            props = operands[1] if len(operands) > 1 and isinstance(operands[1], Dictionary) else None
            mcid = props.get("/MCID") if props is not None else None
            if mcid is not None and tag == "/Artifact":
                owner, owners = _owner(pdf, page_obj, int(mcid))
                if owner is None or "artifact" in str(owner.get("/S")).lower():
                    # decoration stays decoration; the tag reference goes
                    new_props = Dictionary({k: v for k, v in props.items() if k != "/MCID"})
                    operations[index] = [[Name.Artifact, new_props] if len(new_props) else [Name.Artifact],
                                         pikepdf.Operator("BDC" if len(new_props) else "BMC")]
                    if owner is not None:
                        _drop_reference(owner, page_obj, int(mcid))
                        result.removed_tags.append(str(owner.get("/S"))[1:])
                    if isinstance(owners, Array) and 0 <= int(mcid) < len(owners):
                        owners[int(mcid)] = None
                    result.kept_decoration += 1
                    mcid = None
                else:
                    # real content: the tag's type replaces the Artifact mark
                    new_props = Dictionary({k: v for k, v in props.items() if k not in _ARTIFACT_ONLY_KEYS})
                    operations[index] = [[owner.get("/S"), new_props], operator]
                    tag = str(owner.get("/S"))
                    result.made_content += 1
                changed = True
            if mcid is not None:
                for entry in stack:
                    if entry["tag"] == "/Artifact":
                        entry["tagged_inside"] = True
            stack.append({"index": index, "tag": tag, "tagged_inside": False})
        elif name == "EMC" and stack:
            entry = stack.pop()
            outer_artifact = any(other["tag"] == "/Artifact" for other in stack)
            if entry["tag"] == "/Artifact" and entry["tagged_inside"]:
                if outer_artifact:
                    result.nested += 1                    # decoration inside decoration: Phase 6
                else:
                    start = entry["index"]
                    artifact_operands = list(operations[start][0])
                    rewrites[start] = (index, _rewrap(operations[start + 1:index], artifact_operands))
                    result.made_content += 1
    if rewrites:
        rebuilt, index = [], 0
        while index < len(operations):
            if index in rewrites:
                end, new_ops = rewrites[index]
                rebuilt.extend(new_ops)
                index = end + 1
            else:
                rebuilt.append(tuple(operations[index]))
                index += 1
        operations = rebuilt
        changed = True
    if changed:
        page_obj["/Contents"] = pdf.make_stream(pikepdf.unparse_content_stream([tuple(op) for op in operations]))
    return result
