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


_LATEX_SYMBOLS = {
    "rightarrow": "→", "to": "→", "leftarrow": "←", "gets": "←", "leftrightarrow": "↔", "Rightarrow": "⇒",
    "Leftarrow": "⇐", "Leftrightarrow": "⇔", "uparrow": "↑", "downarrow": "↓", "times": "×", "cdot": "·",
    "pm": "±", "leq": "≤", "le": "≤", "geq": "≥", "ge": "≥", "neq": "≠", "ne": "≠", "approx": "≈",
    "sim": "~", "infty": "∞", "degree": "°", "circ": "°", "%": "%", "&": "&",
}
_LATEX_COMMAND = re.compile(r"\\(" + "|".join(re.escape(name) for name in sorted(_LATEX_SYMBOLS, key=len, reverse=True))
                            + r")(?![A-Za-z])")
_DEGREE = re.compile(r"\^\{?\\circ\}?")
_INLINE_MATH = re.compile(r"(?<!\\)\$(?!\s)([^$\n]{1,120}?)(?<![\s\\])\$")
_MARKDOWN = re.compile(r"(\*\*|__|`)(.+?)\1")
# 1.1: notation the AI copies from a figure: "q_alpha" -> "q alpha", "x^2" -> "x²" (a screen reader would say
# "underscore" or "caret"). Only a single letter before "_" or "^", so names like file_name stay as they are.
_SUBSCRIPT = re.compile(r"(?<![\w\\])([A-Za-z])_(?:\{([^{}\s]{1,12})\}|([A-Za-z0-9]{1,8})(?!\w))")
_SUPERSCRIPT = re.compile(r"(?<=[A-Za-z0-9)])\^(?:\{(-?[0-9]{1,3})\}|(-?[0-9]{1,3})(?!\w|\.\d))")
_SUPERSCRIPT_DIGITS = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def spoken_text(text: str) -> str:
    """
    Turns maths notation and Markdown that some models write into plain text that a screen reader
    reads well: 'PDF $\\rightarrow$ Tags' becomes 'PDF → Tags', '**Chart**' becomes 'Chart'.
    Amounts such as '$5 to $10' stay as they are.
    """
    def maths(match: re.Match) -> str:
        inner = match.group(1)
        if not any(sign in inner for sign in "\\^_{"):
            return match.group(0)                                    # not maths, e.g. an amount of money
        return inner.replace("{", "").replace("}", "")
    text = _DEGREE.sub("°", text)
    text = _INLINE_MATH.sub(maths, text)
    text = _LATEX_COMMAND.sub(lambda match: _LATEX_SYMBOLS[match.group(1)], text)
    text = _MARKDOWN.sub(r"\2", text)
    text = _SUBSCRIPT.sub(lambda match: match.group(1) + " " + (match.group(2) or match.group(3)), text)
    text = _SUPERSCRIPT.sub(lambda match: (match.group(1) or match.group(2)).translate(_SUPERSCRIPT_DIGITS), text)
    return " ".join(text.split())


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


# 1.1: characters an AI may propose for a glyph whose Unicode value is missing or invalid. Letters, digits,
# punctuation, maths and currency signs, combining marks (accents, the vector arrow U+20D7) and the symbol blocks
# used in documents (arrows, letterlike, number forms, shapes and bullets, check marks). Never control or private
# characters, never the replacement character, never rare technical symbols nobody can verify.
_SYMBOL_BLOCKS = ((0x2100, 0x21FF), (0x2200, 0x22FF), (0x25A0, 0x25FF), (0x2700, 0x27BF), (0x27C0, 0x27EF),
                  (0x2980, 0x2AFF), (0x00A9, 0x00AE), (0x00B0, 0x00B0))


def plausible_character(codepoint: int) -> bool:
    """Whether an AI's proposal for a glyph may be written into the PDF (see above)."""
    import unicodedata

    if codepoint in (0x0020, 0xFFFD, 0xFEFF, 0xFFFE) or not 0 < codepoint <= 0x10FFFF:
        return False
    category = unicodedata.category(chr(codepoint))
    if category[0] in "LNP" or category in ("Sm", "Sc", "Mn", "Mc"):
        return True
    return category in ("So", "Sk") and any(low <= codepoint <= high for low, high in _SYMBOL_BLOCKS)

