"""Shared structure and text-context helpers for the heading correctors."""

import io
from dataclasses import dataclass

import pdfplumber
from pikepdf import Array, Dictionary, Name, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation


_MAX_NODE_TEXT_LENGTH = 2000


@dataclass
class TextContext:
    """Extracted text indexed by PDF page and marked-content identifier."""

    words_by_page_and_mcid: dict[tuple[int, int], list[str]]
    page_index_by_objgen: dict[tuple[int, int], int]


_TEXT_CONTEXT_CACHE: dict[int, tuple[tuple, TextContext]] = {}


def extract_text_context(
    pdf: Pdf,
    detected_violation: DetectedViolation,
) -> TextContext:
    """Extract tagged words from every page and index the PDF page objects. The result is kept
    for the document: changes to the tags do not change the words on the pages (Phase 5)."""
    key = tuple(page.obj.objgen for page in pdf.pages)
    cached = _TEXT_CONTEXT_CACHE.get(id(pdf))
    if cached is not None and cached[0] == key:
        return cached[1]
    context = _extract_text_context(pdf, detected_violation)
    _TEXT_CONTEXT_CACHE.clear()
    _TEXT_CONTEXT_CACHE[id(pdf)] = (key, context)
    return context


def _extract_text_context(
    pdf: Pdf,
    detected_violation: DetectedViolation,
) -> TextContext:
    """Extract tagged words from every page and index the PDF page objects."""
    snapshot = io.BytesIO()
    try:
        pdf.save(snapshot)
        snapshot.seek(0)
        words_by_page_and_mcid: dict[tuple[int, int], list[str]] = {}
        with pdfplumber.open(snapshot) as extracted_pdf:
            for page_index, page in enumerate(extracted_pdf.pages):
                for word in page.extract_words(extra_attrs=["mcid"]):
                    mcid = word.get("mcid")
                    text = word.get("text")
                    if isinstance(mcid, int) and isinstance(text, str) and text.strip():
                        words_by_page_and_mcid.setdefault(
                            (page_index, mcid), []
                        ).append(text.strip())
    except Exception as exception:
        raise _correction_error(
            detected_violation, "could not extract tagged page text"
        ) from exception

    page_index_by_objgen: dict[tuple[int, int], int] = {}
    for page_index, page in enumerate(pdf.pages):
        objgen = _objgen_tuple(page)
        if objgen != (0, 0):
            page_index_by_objgen[objgen] = page_index
    return TextContext(words_by_page_and_mcid, page_index_by_objgen)


def element_text(
    element: Dictionary,
    page_index: int | None,
    text_context: TextContext,
) -> str | None:
    """Combine accessible metadata and directly owned marked-content text."""
    parts: list[str] = []
    metadata = metadata_text(element)
    if metadata:
        parts.append(metadata)

    if page_index is not None:
        for mcid in _direct_mcids(element):
            words = text_context.words_by_page_and_mcid.get((page_index, mcid), [])
            if words:
                parts.append(" ".join(words))

    text = " ".join(dict.fromkeys(parts)).strip()
    return text[:_MAX_NODE_TEXT_LENGTH] or None


def metadata_text(element: Dictionary) -> str | None:
    """Read accessible text metadata that may describe a structure element."""
    parts = [
        str(value).strip()
        for key in ("/ActualText", "/Alt", "/E", "/T")
        if (value := element.get(key)) is not None and str(value).strip()
    ]
    return " ".join(dict.fromkeys(parts))[:_MAX_NODE_TEXT_LENGTH] or None


def page_index_for_element(
    element: Dictionary,
    inherited_page_index: int | None,
    page_index_by_objgen: dict[tuple[int, int], int],
) -> int | None:
    """Resolve an element's page or retain the page inherited from its parent."""
    page = element.get("/Pg")
    if isinstance(page, Dictionary):
        return page_index_by_objgen.get(
            _objgen_tuple(page), inherited_page_index
        )
    return inherited_page_index


def structure_children(element: Dictionary) -> list[Dictionary]:
    """Return child structure elements from a scalar or array-valued /K entry."""
    children = element.get("/K")
    values = list(children) if isinstance(children, Array) else [children]
    return [
        value
        for value in values
        if isinstance(value, Dictionary) and value.get("/S") is not None
    ]


def get_role_map(pdf: Pdf) -> Dictionary | None:
    """Return the document RoleMap used by custom structure element names."""
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(structure_tree_root, Dictionary):
        return None
    role_map = structure_tree_root.get("/RoleMap")
    return role_map if isinstance(role_map, Dictionary) else None


def resolve_role(role: object, role_map: Dictionary | None) -> object:
    """Resolve custom structure roles while protecting against RoleMap cycles."""
    if role_map is None:
        return role

    current = role
    visited: set[str] = set()
    while isinstance(current, Name):
        role_name = str(current)
        if role_name in visited or role_name not in role_map:
            break
        visited.add(role_name)
        mapped_role = role_map.get(role_name)
        if not isinstance(mapped_role, Name):
            break
        current = mapped_role
    return current


def element_identity(element: Dictionary) -> tuple[int, int] | int:
    """Return a stable key for direct and indirect pikepdf dictionaries."""
    objgen = _objgen_tuple(element)
    return objgen if objgen != (0, 0) else id(element)


def same_element(first: Dictionary, second: Dictionary) -> bool:
    """Compare direct or indirect pikepdf structure dictionaries safely."""
    first_objgen = _objgen_tuple(first)
    second_objgen = _objgen_tuple(second)
    return first is second or first == second or (
        first_objgen != (0, 0) and first_objgen == second_objgen
    )


def _direct_mcids(element: Dictionary) -> list[int]:
    """Return MCIDs owned directly by an element, excluding child StructElems."""
    mcids: list[int] = []

    def collect(value: object) -> None:
        if isinstance(value, int):
            mcids.append(value)
        elif isinstance(value, Array):
            for item in value:
                collect(item)
        elif isinstance(value, Dictionary):
            if value.get("/S") is not None:
                return
            mcid = value.get("/MCID")
            if mcid is not None:
                try:
                    mcids.append(int(str(mcid)))
                except (TypeError, ValueError, OverflowError):
                    return

    collect(element.get("/K"))
    return mcids


def _objgen_tuple(element: object) -> tuple[int, int]:
    """Normalize pikepdf's broadly typed objgen property to an integer tuple."""
    objgen = getattr(element, "objgen", None)
    if (
        isinstance(objgen, tuple)
        and len(objgen) == 2
        and isinstance(objgen[0], int)
        and isinstance(objgen[1], int)
    ):
        return (objgen[0], objgen[1])
    return (0, 0)


def _correction_error(
    detected_violation: DetectedViolation,
    reason: str,
) -> CouldNotCorrectDetectedViolationException:
    """Create a correction exception containing the violation name and reason."""
    return CouldNotCorrectDetectedViolationException(
        f"{detected_violation.violation.name}: {reason}"
    )


__all__ = [
    "TextContext",
    "element_identity",
    "element_text",
    "extract_text_context",
    "get_role_map",
    "metadata_text",
    "page_index_for_element",
    "resolve_role",
    "same_element",
    "structure_children",
]
