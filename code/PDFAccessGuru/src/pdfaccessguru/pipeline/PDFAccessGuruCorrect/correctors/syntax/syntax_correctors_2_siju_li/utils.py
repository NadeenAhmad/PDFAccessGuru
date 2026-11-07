import re

from pikepdf import Array, Name, Pdf, String, Dictionary
import pikepdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.exceptions.corrector_exceptions.could_not_extract_children_exception import (
    CouldNotExtractChildrenException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation

DEFAULT_LANG = "de-DE"
_LANG_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?(?:-[A-Za-z0-9]{2,8})*$")


def normalize_lang_tag(value: object | None) -> str | None:
    if value is None:
        return None

    lang = str(value).strip()
    if not lang:
        return None
    if lang.startswith("/"):
        lang = lang[1:]
    lang = lang.replace("_", "-")

    parts = [part for part in lang.split("-") if part]
    if not parts:
        return None

    parts[0] = parts[0].lower()
    if len(parts) > 1 and len(parts[1]) == 2:
        parts[1] = parts[1].upper()

    normalized = "-".join(parts)
    return normalized if _LANG_RE.match(normalized) else None


def find_language(pdf: Pdf, element: object | None = None) -> str:
    current = element
    visited: set[int] = set()

    while isinstance(current, Dictionary) and id(current) not in visited:
        visited.add(id(current))
        lang = normalize_lang_tag(current.get("/Lang"))
        if lang is not None:
            return lang
        current = current.get("/P")

    catalog_lang = normalize_lang_tag(pdf.Root.get("/Lang"))
    if catalog_lang is not None:
        return catalog_lang

    return DEFAULT_LANG


def normalize_children_of_element(element: pikepdf.Object) -> list:
    if not isinstance(element, Dictionary):
        raise CouldNotExtractChildrenException(element)
    if "/K" not in element:
        return []

    children = element["/K"]
    if isinstance(children, Array):
        return list(children)
    return [children]


def set_children_of_element(element: pikepdf.Object, children: list) -> None:
    if not isinstance(element, Dictionary):
        raise CouldNotExtractChildrenException(element)
    element["/K"] = Array(children)


def normalize_kids(element: pikepdf.Object) -> list:
    """Helper to safely extract kids as a Python list."""
    if '/K' not in element:
        return []
    kids = element['/K']
    if isinstance(kids, pikepdf.Dictionary):
        return [kids]
    if isinstance(kids, pikepdf.Array):
        return list(kids)
    return [kids]  # Handles content items/primitive objects


def correct_table_section_missing(
        detected_violation: DetectedViolation,
        pdf: Pdf,
        section_tag: Name,
        violation_name: str):
    """
    Shared helper for 7.2-5 (THead), 7.2-6 (TBody), 7.2-7 (TFoot).

    The affected element is the misplaced section element (THead/TBody/TFoot).
    Fix: find the nearest Table ancestor and move the section element directly under it.

    Before:
        /Document
            |_/THead   <- wrong position

    After:
        /Document
            |_/Table
                |_/THead
    """
    section_element = detected_violation.affected_element
    parent = section_element.get('/P')

    if parent is None:
        raise CouldNotCorrectDetectedViolationException(violation_name)

    # Find nearest Table in siblings
    def find_table(node: pikepdf.Object) -> pikepdf.Object | None:
        kids = normalize_kids(node)
        for kid in kids:
            if isinstance(kid, pikepdf.Dictionary) and kid.get('/S') == Name('/Table'):
                return kid
        return None

    table = find_table(parent)
    if table is None:
        raise CouldNotCorrectDetectedViolationException(violation_name)

    # Remove section from current parent
    if '/K' in parent:
        p_kids = parent['/K']
        if isinstance(p_kids, pikepdf.Array):
            parent['/K'] = Array([k for k in p_kids if k != section_element])
        elif p_kids == section_element:
            del parent['/K']

    # Add section directly under Table
    table_kids = normalize_kids(table)
    table_kids.append(section_element)
    table['/K'] = Array(table_kids)
    section_element['/P'] = table
