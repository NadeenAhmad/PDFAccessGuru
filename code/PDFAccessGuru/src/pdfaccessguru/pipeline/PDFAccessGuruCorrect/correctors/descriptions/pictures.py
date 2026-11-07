"""
Picture descriptions without an AI (rule 7.3-1), best source first:
1. the picture's caption ("Figure 3: Results of the survey"), from the tags or the page text;
2. text drawn inside the picture (labels of a chart or diagram);
3. text recognised in the picture image (OCR), if the free program Tesseract is installed;
4. otherwise just "Picture", listed for checking.
"""

from __future__ import annotations

import re
import shutil
import subprocess

from pikepdf import Dictionary, Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.layout import Layout
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles, kids

CAPTION_START = re.compile(r"^\s*(fig(ure)?\.?|abb(ildung)?\.?|image|bild|chart|diagram|grafik|foto|photo)\s*\d",
                           re.IGNORECASE)
_WORDS = {"en": ("Picture", "Picture with the text"), "de": ("Abbildung", "Abbildung mit dem Text")}


def _words(pdf: Pdf) -> tuple[str, str]:
    return _WORDS["de" if str(pdf.Root.get("/Lang", "")).lower().startswith("de") else "en"]


def _clean(text: str, limit: int = 200) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + " ..."


def _caption_from_tags(pdf: Pdf, figure: Dictionary, layout: Layout) -> str | None:
    roles = Roles(pdf)
    candidates = [kid for kid in kids(figure) if roles.is_(kid, "Caption")]
    parent = figure.get("/P")
    siblings = kids(parent) if isinstance(parent, Dictionary) else []
    for index, sibling in enumerate(siblings):
        if isinstance(sibling, Dictionary) and sibling.is_indirect and figure.is_indirect \
                and sibling.objgen == figure.objgen:
            for neighbour in siblings[max(0, index - 1):index] + siblings[index + 1:index + 2]:
                if roles.is_(neighbour, "Caption"):
                    candidates.append(neighbour)
                elif roles.is_(neighbour, "P") and CAPTION_START.match(layout.text(neighbour, spaced=True) or ""):
                    candidates.append(neighbour)
    for candidate in candidates:
        text = layout.text(candidate, spaced=True)
        if text and sum(char.isalpha() for char in text) >= 3:
            return _clean(text)
    return None


def _ocr(png: bytes) -> str:
    program = shutil.which("tesseract")
    if program is None or not png:
        return ""
    try:
        done = subprocess.run([program, "stdin", "stdout"], input=png, capture_output=True, timeout=60)
        return done.stdout.decode("utf-8", errors="ignore")
    except (OSError, subprocess.SubprocessError):
        return ""


def describe_picture(pdf: Pdf, figure: Dictionary, png: bytes | None, page_text: str | None) -> tuple[str, str]:
    """(description, source) where source is caption, text, ocr or none."""
    generic, with_text = _words(pdf)
    layout = Layout(pdf)
    caption = _caption_from_tags(pdf, figure, layout)
    if caption is None and page_text:
        caption = next((_clean(line) for line in page_text.splitlines() if CAPTION_START.match(line)), None)
    if caption:
        return caption, "caption"
    inside = layout.text(figure, spaced=True)
    if inside and len(re.findall(r"[^\W\d_]{2,}", inside)) >= 2:
        return f"{with_text}: {_clean(inside)}", "text"
    recognised = _ocr(png or b"")
    if len(re.findall(r"[^\W\d_]{3,}", recognised)) >= 3:
        return f"{with_text}: {_clean(recognised)}", "ocr"
    return generic, "none"
