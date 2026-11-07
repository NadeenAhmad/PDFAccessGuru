import re

import pikepdf
from pikepdf import Array, Dictionary, Name, Pdf, String

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.exceptions.corrector_exceptions.could_not_extract_children_exception import (
    CouldNotExtractChildrenException,
)
from pdfaccessguru.pipeline.reporting.writer import report_review

DEFAULT_LANG = "de-DE"
_LANG_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?(?:-[A-Za-z0-9]{2,8})*$")


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


def is_struct_elem(element: object, struct_type: str) -> bool:
    return isinstance(element, Dictionary) and element.get("/S") == Name(f"/{struct_type}")


def make_struct_elem(pdf: Pdf, struct_type: str, parent: pikepdf.Object, child: object | None = None) -> pikepdf.Object:
    struct_elem = Dictionary({
        "/Type": Name("/StructElem"),
        "/S": Name(f"/{struct_type}"),
        "/P": parent,
    })
    if child is not None:
        struct_elem["/K"] = child
    return pdf.make_indirect(struct_elem)


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


def has_valid_language(pdf: Pdf, element: object | None = None) -> bool:
    if isinstance(element, Dictionary) and normalize_lang_tag(element.get("/Lang")) is not None:
        return True
    return normalize_lang_tag(pdf.Root.get("/Lang")) is not None


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

    return _default_language()


def _default_language() -> str:
    report_review(f"The language could not be determined and was set to the default '{DEFAULT_LANG}'. Please check it.")
    return DEFAULT_LANG


def _set_document_language_if_missing(pdf: Pdf, lang: str) -> None:
    """Set /Lang on the catalog only if the document has no valid language yet.
    An element's language must never overwrite the language of the whole document."""
    if normalize_lang_tag(pdf.Root.get("/Lang")) is None:
        pdf.Root["/Lang"] = String(lang)


def set_language(element: object, pdf: Pdf, violation_name: str) -> None:
    if has_valid_language(pdf, element):
        return

    lang = find_language(pdf, element)
    set_language_value(element, pdf, violation_name, lang)


def set_language_value(element: object, pdf: Pdf, violation_name: str, lang: str) -> None:
    normalized = normalize_lang_tag(lang)
    if normalized is None:
        normalized = _default_language()

    target = element if isinstance(element, Dictionary) else pdf.Root
    if not isinstance(target, Dictionary):
        raise CouldNotCorrectDetectedViolationException(violation_name)
    target["/Lang"] = String(normalized)
    _set_document_language_if_missing(pdf, normalized)


def set_page_or_catalog_language(element: object, pdf: Pdf, violation_name: str) -> None:
    if has_valid_language(pdf, element):
        return

    target = element if isinstance(element, Dictionary) else pdf.Root
    if not isinstance(target, Dictionary):
        raise CouldNotCorrectDetectedViolationException(violation_name)
    lang = find_language(pdf, target)
    target["/Lang"] = String(lang)
    _set_document_language_if_missing(pdf, lang)


def normalize_or_set_language(element: object, pdf: Pdf, violation_name: str) -> None:
    target = element if isinstance(element, Dictionary) else pdf.Root
    if not isinstance(target, Dictionary):
        raise CouldNotCorrectDetectedViolationException(violation_name)

    normalized = normalize_lang_tag(target.get("/Lang"))
    if normalized is None:
        normalized = find_language(pdf, target.get("/P"))
    # Also rewrite values that only needed normalising (e.g. "en_US" -> "en-US").
    if str(target.get("/Lang", "")) != normalized:
        target["/Lang"] = String(normalized)
    _set_document_language_if_missing(pdf, normalized)
