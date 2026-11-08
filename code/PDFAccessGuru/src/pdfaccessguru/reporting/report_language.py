"""
The report is written in the language of the PDF (Phase 7b, decided by the project owner): an
English lecture gets an English report even on a computer set to Arabic, because the person who
fixes the file works with its text.

English and German are built in. Any other language is translated from English by the AI the
user chose (the same one that writes picture descriptions), one sentence at a time. Each
translation is kept on this computer, so later reports in that language are fast. Without an AI
the report stays in English and says so at the top.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BUILT_IN = ("en", "de")

# English names, for the note at the top of an untranslated report and for the AI prompt.
LANGUAGE_NAMES = {
    "ar": "Arabic", "bg": "Bulgarian", "bn": "Bengali", "ca": "Catalan", "cs": "Czech", "da": "Danish",
    "de": "German", "el": "Greek", "en": "English", "es": "Spanish", "et": "Estonian", "fa": "Persian",
    "fi": "Finnish", "fr": "French", "he": "Hebrew", "hi": "Hindi", "hr": "Croatian", "hu": "Hungarian",
    "id": "Indonesian", "it": "Italian", "ja": "Japanese", "ko": "Korean", "lt": "Lithuanian", "lv": "Latvian",
    "ms": "Malay", "nl": "Dutch", "no": "Norwegian", "nb": "Norwegian", "pl": "Polish", "pt": "Portuguese",
    "ro": "Romanian", "ru": "Russian", "sk": "Slovak", "sl": "Slovenian", "sr": "Serbian", "sv": "Swedish",
    "sw": "Swahili", "ta": "Tamil", "th": "Thai", "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu",
    "vi": "Vietnamese", "zh": "Chinese",
}

# Scripts written from right to left: the report pages get dir="rtl".
RIGHT_TO_LEFT = {"ar", "he", "fa", "ur", "ps", "yi", "dv", "ckb", "sd", "ug"}

_NOT_A_LANGUAGE = {"x", "und", "mul", "zxx", "mis"}


def language_name(language: str) -> str:
    return LANGUAGE_NAMES.get(language, language)


def text_direction(language: str) -> str:
    return "rtl" if language in RIGHT_TO_LEFT else "ltr"


def report_language(pdf_path: str | Path) -> str:
    """
    The language of the report for a fixed PDF: the main part of its language tag ("en-GB" ->
    "en"). If the file has no language, it is detected from the text of the first pages.
    English if nothing is known.
    """
    import pikepdf

    try:
        with pikepdf.open(pdf_path) as pdf:
            tag = str(pdf.Root.get("/Lang") or "")
    except Exception:
        tag = ""
    base = tag.strip().split("-")[0].lower()
    if base.isalpha() and 2 <= len(base) <= 3 and base not in _NOT_A_LANGUAGE:
        return base
    try:
        import pymupdf as fitz
        from pdfaccessguru.LLM.fallback import detect_language

        with fitz.open(pdf_path) as document:
            text = " ".join(document[index].get_text() for index in range(min(3, document.page_count)))
        detected = detect_language(text)
    except Exception:
        detected = None
    return detected.split("-")[0].lower() if detected else "en"


# ---------------------------------------------------------------- translation of the report

# Kept as they are: texts quoted from the document (“…”, „…“, "…", «…»), commands ('…'),
# file names and link targets. The AI sees them as ⟦0⟧, ⟦1⟧, ...
_KEEP = re.compile(r"“[^”]*”|„[^“”]*[“”]|\"[^\"]*\"|«[^»]*»|(?<!\w)'[^']+'(?!\w)|`[^`]*`"
                   r"|\]\([^)]*\)|\S+\.(?:pdf|png|md|json)\b|https?://\S+")
_TOKEN = re.compile(r"⟦(\d+)⟧")
_ROW_SEPARATOR = re.compile(r"^\|[\s:|-]+\|$")
_IMAGE_LINE = re.compile(r"^!\[([^\]]*)\](\([^)]*\))\s*$")
_BATCH = 25


def _cache_file(language: str) -> Path:
    from pdfaccessguru.external_tools import tools_dir

    return tools_dir().parent / "translations" / f"{language}.json"


def _load_cache(language: str) -> dict[str, str]:
    try:
        return json.loads(_cache_file(language).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_cache(language: str, cache: dict[str, str]) -> None:
    try:
        path = _cache_file(language)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    except OSError:
        pass                                   # a cache that cannot be written only costs time


def _needs_translation(text: str) -> bool:
    return any(char.isalpha() for char in _KEEP.sub("", text))


def _split(markdown: str) -> list[tuple[str, list[str], str]]:
    """Each line as (before, texts to translate, after); table rows give one text per cell."""
    parts = []
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped or _ROW_SEPARATOR.match(stripped):
            parts.append((line, [], ""))
        elif (image := _IMAGE_LINE.match(stripped)):
            parts.append(("![", [image.group(1)], "]" + image.group(2)))
        elif stripped.startswith("|") and stripped.endswith("|"):
            parts.append(("|", [cell.strip() for cell in stripped[1:-1].split("|")], "|"))
        else:
            prefix = re.match(r"^(\s*(?:#{1,6}\s+|[-*]\s+|\d+\.\s+)?)", line).group(1)
            parts.append((prefix, [line[len(prefix):]], ""))
    return parts


def _protect(text: str) -> tuple[str, list[str]]:
    kept: list[str] = []

    def keep(match: re.Match) -> str:
        kept.append(match.group(0))
        return f"⟦{len(kept) - 1}⟧"

    return _KEEP.sub(keep, text), kept


def _restore(text: str, kept: list[str]) -> str | None:
    """Put the kept pieces back; None if the AI lost or added one."""
    if sorted(int(n) for n in _TOKEN.findall(text)) != list(range(len(kept))):
        return None
    return _TOKEN.sub(lambda match: kept[int(match.group(1))], text)


def _ask_ai(texts: list[str], language: str) -> list[str | None]:
    from pdfaccessguru.LLM.client import LLMClient

    system = (
        f"You translate short texts from an accessibility report from English into {language_name(language)} "
        f"(language code {language}). Write plain, simple, polite sentences for people who are not experts. "
        "Keep every marker like ⟦0⟧ exactly as it is, in a fitting place. Keep numbers and the words "
        "PDF, veraPDF, Ollama, OpenRouter and OpenAI. Answer only with JSON: {\"t\": [one translation per "
        "input text, in the same order]}."
    )
    answer = LLMClient().send_message(system, json.dumps({"texts": texts}, ensure_ascii=False), json_mode=True)
    translated = json.loads(answer).get("t")
    if not isinstance(translated, list) or len(translated) != len(texts):
        return [None] * len(texts)
    return [text if isinstance(text, str) and text.strip() else None for text in translated]


def translate_markdown(markdown: str, language: str, progress=None) -> tuple[str, str | None]:
    """
    The report in `language`, translated from English. Returns (markdown, note): the note says
    in English why the report is (partly) in English, or None if all of it was translated.
    """
    if language in BUILT_IN:
        return markdown, None
    from pdfaccessguru.LLM.fallback import ai_available

    name = language_name(language)
    if not ai_available():
        return markdown, (f"This report is in English. The PDF is in {name}, but no AI is set up to translate "
                          f"the report. With an AI (for example Ollama, free on this computer), the report is "
                          f"written in {name}.")
    parts = _split(markdown)
    cache = _load_cache(language)
    protected = {}
    for _, texts, _ in parts:
        for text in texts:
            if _needs_translation(text) and text not in cache and text not in protected:
                protected[text] = _protect(text)
    missing = list(protected)
    failed = 0
    for start in range(0, len(missing), _BATCH):
        batch = missing[start:start + _BATCH]
        if progress:
            progress(start / max(1, len(missing)))
        try:
            answers = _ask_ai([protected[text][0] for text in batch], language)
        except Exception:
            answers = [None] * len(batch)
        for text, answer in zip(batch, answers):
            restored = _restore(answer, protected[text][1]) if answer else None
            if restored is None:
                failed += 1
            else:
                cache[text] = restored
    if missing:
        _save_cache(language, cache)

    lines = []
    for before, texts, after in parts:
        if not texts:
            lines.append(before)
            continue
        translated = [cache.get(text, text) if _needs_translation(text) else text for text in texts]
        if before == "|":
            lines.append("| " + " | ".join(translated) + " |")
        else:
            lines.append(before + translated[0] + after)
    note = None
    if failed:
        note = f"Some sentences of this report stay in English: the AI could not translate them into {name}."
    return "\n".join(lines) + ("\n" if markdown.endswith("\n") else ""), note
