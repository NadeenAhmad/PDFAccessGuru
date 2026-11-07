"""
Measures how much of a document's text is reachable for screen readers.

Every text-showing operator (Tj, TJ, ', ") in the page content streams and the form
XObjects they use is classified as
- tagged:   inside a marked-content sequence that is not an artifact (real content),
- artifact: inside an /Artifact sequence (ignored by assistive technology),
- untagged: outside any marked-content sequence.

The counts are operators, not characters; they are meant for comparing a document before
and after correction (e.g. to see whether text was hidden as artifacts).
"""

from __future__ import annotations

import pikepdf

_TEXT_SHOWING = {"Tj", "TJ", "'", '"'}


def _count_stream(holder: pikepdf.Object, counts: dict[str, int], visited: set, depth: int = 0) -> None:
    if depth > 10:
        return
    try:
        instructions = pikepdf.parse_content_stream(holder)
    except Exception:
        return

    stack: list[str] = []
    for operands, operator in instructions:
        name = str(operator)
        if name in ("BDC", "BMC"):
            stack.append(str(operands[0]) if operands else "")
        elif name == "EMC":
            if stack:
                stack.pop()
        elif name in _TEXT_SHOWING:
            if "/Artifact" in stack:
                counts["artifact"] += 1
            elif any(tag not in ("/OC", "") for tag in stack):
                # /OC only marks optional content (layers); it is not a structure tag.
                counts["tagged"] += 1
            else:
                counts["untagged"] += 1

    resources = holder.get("/Resources") if hasattr(holder, "get") else None
    xobjects = resources.get("/XObject") if isinstance(resources, pikepdf.Dictionary) else None
    if not isinstance(xobjects, pikepdf.Dictionary):
        return
    for key in list(xobjects.keys()):
        xobject = xobjects[key]
        if not isinstance(xobject, pikepdf.Stream) or xobject.get("/Subtype") != pikepdf.Name.Form:
            continue
        object_id = xobject.objgen
        if object_id in visited:
            continue
        visited.add(object_id)
        _count_stream(xobject, counts, visited, depth + 1)


def measure_text_tagging(pdf: pikepdf.Pdf) -> dict[str, float | int]:
    """Return the number of tagged / artifact / untagged text operators and the tagged share."""
    counts = {"tagged": 0, "artifact": 0, "untagged": 0}
    visited: set = set()
    for page in pdf.pages:
        _count_stream(page.obj, counts, visited)
    total = sum(counts.values())
    return {
        **counts,
        "total": total,
        "tagged_share": counts["tagged"] / total if total else 0.0,
    }
