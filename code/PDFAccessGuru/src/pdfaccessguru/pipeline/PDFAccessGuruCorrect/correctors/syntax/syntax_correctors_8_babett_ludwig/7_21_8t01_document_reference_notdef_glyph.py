"""
VeraPdf rule_id: 7.21.8-1 (and with it 7.21.7-2 for the same characters)

Violation description:
The text shows the .notdef glyph, the "no glyph" placeholder.

What the real cases are (Phase 11, found in real web PDFs): tab, carriage return and other control
characters (codes below 32) written into the text of simple fonts, e.g. `(\t) Tj`. No standard
encoding gives these codes a glyph, so they show nothing, and screen readers get an invalid
character (Unicode 0).

Correction strategy (rewritten; the first version deleted characters without keeping their gap):
control characters without a glyph are removed from the text of simple fonts (Type 1, TrueType).
Where the font gives such a code a width, a text shift of exactly that width takes its place, so
every following letter stays where it was. Composite fonts (Type 0) are never changed: there,
low codes are real characters, and a missing glyph cannot be repaired by editing the text.
The page check of the font stage makes sure nothing on the page looks different.
"""

from __future__ import annotations

import pikepdf
from pikepdf import Array, Dictionary, Name, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_debug

_SHOW = {"Tj", "TJ", "'", '"'}
_SIMPLE = {Name.Type1, Name.TrueType, Name.MMType1}


def _empty_codes(font) -> set[int] | None:
    """Codes below 32 that have no glyph in a simple font (None: not a simple font, leave it)."""
    if not isinstance(font, Dictionary) or font.get("/Subtype") not in _SIMPLE:
        return None
    named: set[int] = set()
    encoding = font.get("/Encoding")
    differences = encoding.get("/Differences") if isinstance(encoding, Dictionary) else None
    if isinstance(differences, Array):
        code = None
        for item in differences:
            if isinstance(item, int) or (isinstance(item, pikepdf.Object) and not isinstance(item, Name)):
                try:
                    code = int(item)
                except (TypeError, ValueError):
                    code = None
            elif isinstance(item, Name) and code is not None:
                if str(item) != "/.notdef":
                    named.add(code)
                code += 1
    return {code for code in range(32) if code not in named}


def _width(font, code: int) -> float:
    widths, first = font.get("/Widths"), font.get("/FirstChar")
    if isinstance(widths, Array) and first is not None and 0 <= code - int(first) < len(widths):
        return float(widths[code - int(first)])
    return 0.0


def _clean(items: list, font, empty: set[int]) -> tuple[list, int]:
    """TJ items without the empty control codes; their width becomes a text shift. Returns (items, removed)."""
    out: list = []
    removed = 0
    for item in items:
        if not isinstance(item, pikepdf.String):
            out.append(item)
            continue
        kept = bytearray()
        for byte in bytes(item):
            if byte in empty:
                removed += 1
                width = _width(font, byte)
                if kept:
                    out.append(pikepdf.String(bytes(kept)))
                    kept = bytearray()
                if width:
                    out.append(-width)               # a TJ number moves back by n/1000 em: -width moves forward
            else:
                kept.append(byte)
        if kept:
            out.append(pikepdf.String(bytes(kept)))
    return out, removed


def _clean_stream(pdf: Pdf, owner, resources) -> int:
    """Clean the text of one content stream (a page or a form XObject). Returns the codes removed."""
    fonts = resources.get("/Font") if isinstance(resources, Dictionary) else None
    try:
        operations = list(pikepdf.parse_content_stream(owner))
    except Exception:
        return 0
    font = empty = None
    out: list = []
    removed = 0
    for operands, operator in operations:
        name = str(operator)
        if name == "Tf" and isinstance(fonts, Dictionary):
            font = fonts.get(str(operands[0]))
            empty = _empty_codes(font)
        if name in _SHOW and empty:
            strings = list(operands[0]) if name == "TJ" else [operands[-1]]
            if any(isinstance(s, pikepdf.String) and any(b in empty for b in bytes(s)) for s in strings):
                cleaned, count = _clean(strings, font, empty)
                removed += count
                if name in ("'", '"'):                   # keep the move to the next line, show the rest
                    out.append(([], pikepdf.Operator("T*")))
                    if name == '"':
                        out.append(([operands[0]], pikepdf.Operator("Tw")))
                        out.append(([operands[1]], pikepdf.Operator("Tc")))
                if cleaned:
                    out.append(([Array(cleaned)], pikepdf.Operator("TJ")))
                continue
        out.append((operands, operator))
    if removed:
        owner_object = owner.obj if isinstance(owner, pikepdf.Page) else owner
        if isinstance(owner, pikepdf.Page):
            owner_object["/Contents"] = pdf.make_stream(pikepdf.unparse_content_stream(out))
        else:
            owner_object.write(pikepdf.unparse_content_stream(out))
    return removed


@corrector("document-reference-notdef-glyph")
def correct_document_reference_notdef_glyph(detected_violation: DetectedViolation, pdf: Pdf):
    """All pages and their form XObjects at once (the rule is document-level in the font stage)."""
    removed = 0
    seen: set = set()
    for page in pdf.pages:
        resources = page.obj.get("/Resources")
        removed += _clean_stream(pdf, page, resources)
        xobjects = resources.get("/XObject") if isinstance(resources, Dictionary) else None
        for xobject in (xobjects.values() if isinstance(xobjects, Dictionary) else []):
            if isinstance(xobject, pikepdf.Stream) and xobject.get("/Subtype") == Name.Form \
                    and xobject.objgen not in seen:
                seen.add(xobject.objgen)
                removed += _clean_stream(pdf, xobject, xobject.get("/Resources") or resources)
    if not removed:
        raise CouldNotCorrectDetectedViolationException(
            "document-reference-notdef-glyph: no control characters without a glyph in simple fonts "
            "(a missing glyph in a composite font cannot be repaired by editing the text)")
    report_debug(f"7.21.8-1: removed {removed} control character(s) without a glyph, keeping their width.")
