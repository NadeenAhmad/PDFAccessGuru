"""
Safe corrections: every group of fixes is checked and undone if it made the file worse.

WorkingDocument keeps the PDF being corrected and can take snapshots and restore them.
judge_fix() decides whether a group of fixes (all occurrences of one rule) is kept:

- undone if the rule itself now has more problems than before,
- undone if it fixed nothing but other problems appeared, or if more new problems appeared
  than it fixed (new problems can be caused or only revealed: veraPDF skips some checks
  until other problems are fixed, so a clearly helpful fix is kept and the new problems are
  listed and handled by the next stages or rounds),
- undone if a page would look different, or (unless the stage may change text, e.g. fixing
  character mappings) if the text of a page would change.
"""

from __future__ import annotations

import io
from collections import Counter
from dataclasses import dataclass

import pymupdf as fitz
import numpy
import pikepdf

from pdfaccessguru.pipeline.stages import Stage

# Share of pixel values that may differ before a page counts as "looking different".
_STRONG_DIFFERENCE = 96        # a channel changes by more than this: a real change
_STRONG_TOLERANCE = 0.00002     # share of pixels that may change strongly (noise only)
_FAINT_TOLERANCE = 0.02         # share of pixels that may change faintly (edge shading)
_RENDER_DPI = 40


class WorkingDocument:
    """The PDF being corrected, with snapshots for undoing a group of fixes."""

    def __init__(self, pdf: pikepdf.Pdf) -> None:
        self.pdf = pdf
        self.encrypted = bool(pdf.is_encrypted)

    @classmethod
    def open(cls, path: str) -> "WorkingDocument":
        from pdfaccessguru.pipeline.protection import open_password
        return cls(pikepdf.open(path, password=open_password()))

    def _save_options(self) -> dict:
        # An encrypted input stays encrypted with its original passwords and permissions, plus
        # the screen-reader permission if the owner password was given (see protection.py).
        from pdfaccessguru.pipeline.protection import save_options
        # Unprotected files are saved byte-for-byte reproducibly, so an unchanged file can be
        # recognised without checking it again (Phase 5).
        return save_options(self.pdf) if self.encrypted else {"deterministic_id": True}

    def save(self, path: str) -> None:
        self.pdf.save(path, **self._save_options())

    def snapshot(self) -> bytes:
        buffer = io.BytesIO()
        self.pdf.save(buffer, **self._save_options())
        return buffer.getvalue()

    def restore(self, snapshot: bytes) -> None:
        self.pdf.close()
        from pdfaccessguru.pipeline.protection import open_password
        self.pdf = pikepdf.open(io.BytesIO(snapshot), password=open_password())

    def close(self) -> None:
        self.pdf.close()


@dataclass(frozen=True)
class Verdict:
    keep: bool
    fixed: int = 0        # problems of this rule that disappeared
    revealed: int = 0     # new problems of the same or later stages (allowed)
    reason: str = ""      # why the fixes were undone (plain language)


def _counts(findings) -> Counter:
    return Counter(finding.rule_id for finding in findings)


def judge_fix(
    rule_id: str,
    stage: Stage,
    before_findings,
    after_findings,
    before_pdf: bytes,
    after_pdf_path: str,
) -> Verdict:
    before, after = _counts(before_findings), _counts(after_findings)
    fixed = before[rule_id] - after[rule_id]
    if fixed < 0:
        return Verdict(False, fixed, reason=f"it caused {-fixed} more problem(s) of the same kind")

    # Findings can be caused by a fix or only revealed by it: veraPDF skips some checks until
    # other problems are fixed (e.g. setting the document language makes it check content and
    # links it skipped before). The two cannot be told apart from the counts, so the net effect
    # over all rules decides: a fix is kept only if more problems disappeared than appeared.
    rules = set(before) | set(after)
    removed = sum(max(0, before[r] - after[r]) for r in rules)
    new_elsewhere = sum(max(0, after[r] - before[r]) for r in rules if r != rule_id)
    if rule_id not in stage.reveals_by_design:
        if removed == 0 and new_elsewhere:
            return Verdict(False, fixed, new_elsewhere, reason=f"it fixed nothing and {new_elsewhere} new problem(s) appeared")
        if new_elsewhere > removed:
            return Verdict(False, fixed, new_elsewhere,
                           reason=f"more new problems appeared ({new_elsewhere}) than disappeared ({removed})")

    reason = None
    if rule_id in stage.shapes_may_change:
        reason = compare_glyph_positions(before_pdf, after_pdf_path)
    elif rule_id in stage.content_rules:
        # Tagging only adds marks around content and never removes or moves anything. Renderers
        # can composite transparent drawings slightly differently once they are marked (seen in
        # MuPDF and Ghostscript, invisible at any zoom), so: every character must stay exactly in
        # place, and pictures may not change visibly (strong change on at most 0.1% of a page).
        reason = compare_glyph_positions(before_pdf, after_pdf_path) or \
            compare_pages(before_pdf, after_pdf_path, compare_all=True, check_text=True, strong_tolerance=0.001)
    elif stage.touches_content:
        reason = compare_pages(before_pdf, after_pdf_path, compare_all=stage.name == "fonts",
                               check_text=not stage.text_may_change)
    if reason:
        return Verdict(False, fixed, new_elsewhere, reason=reason)
    return Verdict(True, removed, new_elsewhere)


def judge_together(rule_ids, stage: Stage, before_findings, after_findings, before_pdf: bytes,
                   after_pdf_path: str) -> str | None:
    """
    Judge several whole-document fixes that were applied together (Phase 5). The same rules as
    for one fix: none of them may cause more problems of its own kind, more problems may not
    appear than disappear, and pages must look the same. Returns the reason to undo, or None.
    """
    before, after = _counts(before_findings), _counts(after_findings)
    for rule_id in rule_ids:
        if after[rule_id] > before[rule_id] and rule_id not in stage.reveals_by_design:
            return f"rule {rule_id} got more problems"
    if not any(rule_id in stage.reveals_by_design for rule_id in rule_ids):
        rules = set(before) | set(after)
        removed = sum(max(0, before[r] - after[r]) for r in rules)
        new_elsewhere = sum(max(0, after[r] - before[r]) for r in rules if r not in rule_ids)
        if new_elsewhere > removed or (removed == 0 and new_elsewhere):
            return "more new problems appeared than disappeared"
    if stage.touches_content:
        return compare_pages(before_pdf, after_pdf_path, compare_all=stage.name == "fonts",
                             check_text=not stage.text_may_change)
    return None


def _looks_different(old_pixels, new_pixels, strong_tolerance: float | None = None) -> bool:
    """
    True if a page changed visibly. Strong differences (a changed, moved or missing glyph or
    picture) count even on a few pixels; faint differences in the shading of glyph edges, which
    renderers produce when content is only marked (tagging), count only if they cover a large
    share of the page (measured in Phase 6: marking gives at most 67 of 255, a deleted line of
    text gives more than 128).
    """
    difference = numpy.abs(old_pixels.astype(numpy.int16) - new_pixels.astype(numpy.int16))
    size = max(difference.size, 1)
    strong = numpy.count_nonzero(difference > _STRONG_DIFFERENCE) / size
    faint = numpy.count_nonzero(difference) / size
    limit = _STRONG_TOLERANCE if strong_tolerance is None else strong_tolerance
    return strong > limit or (strong_tolerance is None and faint > _FAINT_TOLERANCE)


def compare_pages(before_pdf: bytes, after_pdf_path: str, compare_all: bool = False, check_text: bool = True,
                  strong_tolerance: float | None = None) -> str | None:
    """
    Compare the pages of two versions. Returns a plain-language reason if a page would look
    different (or its text would change), else None. Only pages whose content changed are
    rendered, unless compare_all is set (e.g. when fonts were changed).
    """
    with fitz.open(stream=before_pdf, filetype="pdf") as old, fitz.open(after_pdf_path) as new:
        if old.page_count != new.page_count:
            return "the number of pages would change"
        for number in range(old.page_count):
            old_page, new_page = old[number], new[number]
            if not compare_all and old_page.read_contents() == new_page.read_contents():
                continue
            old_pixels = numpy.frombuffer(old_page.get_pixmap(dpi=_RENDER_DPI).samples, dtype=numpy.uint8)
            new_pixels = numpy.frombuffer(new_page.get_pixmap(dpi=_RENDER_DPI).samples, dtype=numpy.uint8)
            if old_pixels.shape != new_pixels.shape:
                return f"page {number + 1} would change its size"
            if _looks_different(old_pixels, new_pixels, strong_tolerance):
                return f"page {number + 1} would look different"
            if check_text and old_page.get_text() != new_page.get_text():
                return f"the text on page {number + 1} would change"
    return None


def _glyphs(page) -> Counter:
    """Every visible character of a page with the point where it is drawn."""
    glyphs: Counter = Counter()
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                for char in span["chars"]:
                    if not char["c"].isspace():
                        glyphs[(round(char["origin"][0], 1), round(char["origin"][1], 1), char["c"])] += 1
    return glyphs


def compare_glyph_positions(before_pdf: bytes, after_pdf_path: str) -> str | None:
    """
    For fixes that may change the shape of letters but nothing else (embedding a font that the
    file lacked, where viewers showed a look-alike before): every character must stay where it
    was. Returns a plain-language reason if not, else None.
    """
    with fitz.open(stream=before_pdf, filetype="pdf") as old, fitz.open(after_pdf_path) as new:
        if old.page_count != new.page_count:
            return "the number of pages would change"
        for number in range(old.page_count):
            if old[number].rect != new[number].rect:
                return f"page {number + 1} would change its size"
            if _glyphs(old[number]) != _glyphs(new[number]):
                return f"characters on page {number + 1} would move, change or disappear"
    return None
