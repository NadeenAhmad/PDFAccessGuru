"""
Minimal checks for text returned by a language model before it is written into a PDF.

A reply is unusable when it is empty, an error or refusal message, or a generic placeholder.
Correctors must fall back (and report the item for review) instead of writing such text.
"""

from __future__ import annotations

import re

_UNUSABLE_PATTERNS = re.compile(
    r"^\s*(error\b|fehler\b)"
    r"|i\s*(cannot|can't|can not|am unable|'m unable|am not able)"
    r"|i'?m sorry|as an ai\b|language model"
    r"|undecipherable|invalid document|no (text|content) (provided|available)"
    r"|not enough (information|context)|unable to (determine|identify|generate)",
    re.IGNORECASE,
)

_GENERIC_TEXTS = {
    "image", "figure", "picture", "photo", "graphic", "link", "url", "title", "document",
    "untitled", "untitled document", "formula", "equation", "n/a", "none", "unknown",
}


def clean_llm_text(text: str | None) -> str:
    """Strip whitespace and surrounding quotes from a model reply."""
    if not text:
        return ""
    return text.strip().strip('"').strip("'").strip()


def is_unusable_llm_text(text: str | None) -> bool:
    """True if the reply must not be written into the PDF."""
    cleaned = clean_llm_text(text)
    if not cleaned:
        return True
    if cleaned.lower().rstrip(".") in _GENERIC_TEXTS:
        return True
    return bool(_UNUSABLE_PATTERNS.search(cleaned))
