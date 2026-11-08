"""
The text of a page as a reader sees it (decoded through the page's fonts with PyMuPDF).

Reading the letter codes straight out of the page content gives garbage for many fonts (Word,
LaTeX and others number their letters their own way: "SCREEN" came out as "TDSFFO"), and
language detection and title suggestions built on that are wrong.
"""

from __future__ import annotations

import io

import pikepdf


def page_text(page_or_element: object) -> str | None:
    """Decoded text of a page (pikepdf Page or page dictionary); None for anything else or on failure."""
    import pymupdf as fitz

    if isinstance(page_or_element, pikepdf.Page):
        page = page_or_element
    elif isinstance(page_or_element, pikepdf.Dictionary) and page_or_element.get("/Type") == pikepdf.Name.Page:
        try:
            page = pikepdf.Page(page_or_element)
        except Exception:
            return None
    else:
        return None
    try:
        single = pikepdf.new()
        single.pages.append(page)                       # copies the page with its fonts and pictures
        buffer = io.BytesIO()
        single.save(buffer)
        with fitz.open(stream=buffer.getvalue(), filetype="pdf") as document:
            text = document[0].get_text("text")
    except Exception:
        return None
    text = " ".join(text.replace("\x00", "").split())
    return text or None
