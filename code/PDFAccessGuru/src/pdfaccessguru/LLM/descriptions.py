"""
Picture descriptions written by an AI (1.1).

How detailed they are: "brief", "standard" (the default) or "detailed". The user picks it in the app (box 2)
or with `fix --descriptions`; it reaches the pipeline as PDFACCESSGURU_DESCRIPTIONS. Descriptions written by
simple rules (caption or nearby text) do not depend on it.

The instructions follow the W3C guidance on text alternatives: say what the picture means, not how it looks;
a short text for a simple picture, the main message and the key values for a chart or diagram. Abbreviations
the document defines ("epithelial-mesenchymal transition (EMT)") are handed to the AI so it can spell them out.
A description that is still too long is cut after its last whole sentence that fits: the instructions put the
main message first, so the end is the least important part.
"""

from __future__ import annotations

import os
import re

LEVELS = ("brief", "standard", "detailed")
DEFAULT_LEVEL = "standard"

# Longest description kept (characters); longer ones are cut after the last whole sentence that fits.
_LIMITS = {"brief": 200, "standard": 600, "detailed": 1200}

_INTRO = """You write the alternative text (alt text) for a figure in a PDF document. A screen reader reads it aloud,
instead of the figure, to a person who cannot see it. The reader should get the figure's message without seeing it.

How to write it:"""

_LENGTH = {
    "brief": """- Write one short sentence (at most about 125 characters) with the figure's main message or purpose.
  For a chart or diagram, give its main finding or what it shows, not every value.""",
    "standard": """- First decide: is it a simple figure (photo, logo, icon, simple illustration or diagram) or a complex one
  (chart, plot, multi-panel figure, detailed diagram)?
- Simple figure: one or two short sentences (at most about 180 characters) saying what it shows and why it is there.
- Complex figure: up to four short sentences (at most about 450 characters). Start with the main message or finding.
  Then say what is shown (what is plotted against what, with units) and the key results or values for each panel
  or group. Leave out details the reader cannot use.""",
    "detailed": """- First decide: is it a simple figure (photo, logo, icon, simple illustration or diagram) or a complex one
  (chart, plot, multi-panel figure, detailed diagram)?
- Simple figure: one to three sentences (at most about 300 characters) saying what it shows and why it is there.
- Complex figure: up to eight short sentences (at most about 1000 characters). Start with the main message or
  finding. Then say what is shown (what is plotted against what, with units), and for each panel or group the key
  values, trends and notable exceptions. For a diagram, name its parts and how they are connected.""",
}

_RULES = """- Describe meaning, not looks. Mention a colour, shape or position only when it carries meaning, and then say what
  it stands for (for example "stable states" rather than "red bars").
- Use the words of the caption and the nearby text. When an abbreviation is listed under "Abbreviations defined in
  this document" or spelled out in the nearby text, write the full term once, followed by the abbreviation in
  parentheses. Otherwise keep the abbreviation as it is; never invent what an abbreviation means.
- Plain text only: no Markdown, no LaTeX, no lists or bullet points, no special symbols a screen reader cannot read.
  Write formulas, symbols and units in words where needed.
- Do not start with "image of" or "picture of", and do not repeat the caption word for word.
- Do not guess details that are neither visible nor stated in the text.
Write in the language of the document. The supplied image is the figure; the JSON gives its place in the document
and the text around it.

Return only JSON in this exact form:
{"alt_text": "Meaningful description"}"""


def level() -> str:
    """The chosen level of detail (PDFACCESSGURU_DESCRIPTIONS), "standard" if none or unknown."""
    chosen = os.environ.get("PDFACCESSGURU_DESCRIPTIONS", "").strip().lower()
    return chosen if chosen in LEVELS else DEFAULT_LEVEL


def length_limit(chosen: str | None = None) -> int:
    """Longest description kept for this level, in characters."""
    return _LIMITS.get(chosen or level(), _LIMITS[DEFAULT_LEVEL])


def system_prompt(chosen: str | None = None) -> str:
    """The instructions for the AI at this level of detail."""
    return f"{_INTRO}\n{_LENGTH.get(chosen or level(), _LENGTH[DEFAULT_LEVEL])}\n{_RULES}"


def user_prompt(context_json: str, abbreviations: list[str] | None = None) -> str:
    """The figure's context (PDF-derived data stays in the user role) and the document's abbreviations."""
    listed = "\n".join("- " + line for line in abbreviations or []) or "(none found)"
    return (f"Figure structure and page context:\n{context_json}\n\n"
            f"Abbreviations defined in this document:\n{listed}")


_SENTENCE_END = re.compile(r"(?<=[.!?。])\s+")


def shorten(text: str, limit: int) -> str:
    """The text cut after its last whole sentence within the limit (a single long sentence: after the last whole
    word, ending with '…')."""
    if len(text) <= limit:
        return text
    kept = ""
    for sentence in _SENTENCE_END.split(text):
        candidate = f"{kept} {sentence}".strip()
        if len(candidate) > limit:
            break
        kept = candidate
    if kept:
        return kept
    words = text[: limit - 1].rsplit(" ", 1)[0].rstrip(" ,;:")
    return words + "…"


# --- abbreviations defined in the document -------------------------------------------------------

_SHORT_IN_BRACKETS = re.compile(r"\(([A-Za-z][A-Za-z0-9-]{1,9})s?\)")
_LONG_IN_BRACKETS = re.compile(r"\b([A-Z][A-Za-z0-9-]{1,9})s?\s+\(([^()]{4,80})\)")
_WORD = re.compile(r"[^\W\d_][^\W_]*(?:-[^\W\d_][^\W_]*)*")
_SMALL_WORDS = {"of", "and", "the", "for", "in", "on", "to", "a", "an", "with", "by", "und", "der", "die", "das",
                "für", "von", "im"}


def _is_short_form(short: str) -> bool:
    return sum(c.isupper() for c in short) >= 2


def _initials(words: list[str]) -> str:
    return "".join(part[0].lower() for word in words for part in word.split("-") if part)


def _matches(short: str, words: list[str]) -> bool:
    """Whether the words are the long form of the short form: the short form's letters are the initials of the words
    (small words like 'of' may be skipped), or appear in order in the words, starting with the first letter."""
    letters = "".join(c.lower() for c in short if c.isalpha())
    if not words or not letters or words[0][0].lower() != letters[0]:
        return False
    if words[0].lower() in _SMALL_WORDS:
        return False
    if _initials(words) == letters or _initials([w for w in words if w.lower() not in _SMALL_WORDS]) == letters:
        return True
    if short.isupper():
        return False
    # mixed case ("CoV", "mRNA"): letters in order inside the words, every word giving at least its first letter
    joined, position = " ".join(words).lower(), 0
    for letter in letters:
        position = joined.find(letter, position)
        if position < 0:
            return False
        position += 1
    content = [w for w in words if w.lower() not in _SMALL_WORDS]
    return len(content) <= len(letters) and all(w[0].lower() in letters for w in content)


def abbreviation_definitions(text: str, limit: int = 25) -> list[str]:
    """'SHORT: long form' for every abbreviation the document defines, in the order first defined, either as
    'long form (SHORT)' or as 'SHORT (long form)'. Only pairs whose letters match are kept: nothing is guessed."""
    found: dict[str, str] = {}
    for match in _SHORT_IN_BRACKETS.finditer(text):
        short = match.group(1)
        if not _is_short_form(short) or short in found:
            continue
        before = _WORD.findall(text[max(0, match.start() - 200):match.start()])
        letters = sum(c.isalpha() for c in short)
        for size in range(1, min(len(before), letters + 3) + 1):
            words = before[-size:]
            if _matches(short, words):
                found[short] = " ".join(words)
                break
    for match in _LONG_IN_BRACKETS.finditer(text):
        short, long_form = match.group(1), match.group(2).strip()
        if not _is_short_form(short) or short in found:
            continue
        words = _WORD.findall(long_form)
        if words and len(words) <= sum(c.isalpha() for c in short) + 3 and _matches(short, words):
            found[short] = " ".join(words)
    return [f"{short}: {long_form}" for short, long_form in list(found.items())[:limit]]
