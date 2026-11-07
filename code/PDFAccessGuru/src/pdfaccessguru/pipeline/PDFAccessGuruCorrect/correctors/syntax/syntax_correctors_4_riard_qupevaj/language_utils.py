import json
import os
from pathlib import Path
from typing import Iterable

import pikepdf
from pikepdf import Dictionary, Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.utils import (
    DEFAULT_LANG,
    normalize_lang_tag,
)

MAX_LANGUAGE_TEXT_LENGTH = 800


def determine_lang_tag(text: str) -> str | None:
    """
    Determine a BCP 47 language tag for text via LLM.

    Returns None if the text is empty, too long, the provider is unavailable, or
    the model returns an invalid language tag. Callers should fall back to the
    inherited document language in that case.
    """
    normalized_text = _normalize_prompt_text(text)
    if normalized_text is None:
        return None

    system_prompt, user_prompt = build_determine_lang_tag_prompt(normalized_text)
    try:
        from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider

        response = OpenRouterBaseProvider().send_message(system_prompt, user_prompt)
    except Exception:
        return None

    return normalize_lang_tag(_strip_response(response))


def build_determine_lang_tag_prompt(text: str) -> tuple[str, str]:
    language_codes = load_available_language_codes()
    system_prompt = (
        "You determine the natural language of short PDF accessibility text. "
        "Return exactly one BCP 47 language tag from this list and no other text: "
        f"{language_codes}"
    )
    user_prompt = f"Text:\n{text}"
    return system_prompt, user_prompt


def choose_language_for_text(text: str | None, pdf: Pdf, element: object | None = None) -> str:
    """
    The language of a text, best source first (Phase 4):
    1. word statistics (py3langid): reliable for real sentences, no AI needed;
    2. the AI model, for short or unclear texts, if one is set up;
    3. the language around the text (its parents, then the document), detected the same way
       from the whole document if the document has none.
    """
    from pdfaccessguru.LLM.fallback import ai_available, detect_language, note_fallback

    detected = detect_language(text)
    if detected is not None:
        return detected
    if text and sum(char.isalpha() for char in text) >= 3:
        if ai_available():
            llm_language = determine_lang_tag(text)
            if llm_language is not None:
                return llm_language
        else:
            note_fallback("language")

    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.utils import find_language

    inherited = find_language(pdf, element) if _has_language_around(pdf, element) else None
    if inherited is not None:
        return inherited
    document_language = detect_language(extract_text_from_document(pdf), min_confidence=0.8)
    if document_language is not None:
        return document_language
    if ai_available():
        llm_language = determine_lang_tag(extract_text_from_document(pdf) or "")
        if llm_language is not None:
            return llm_language
    return find_language(pdf, element)


def _has_language_around(pdf: Pdf, element: object | None) -> bool:
    current, steps = element, 0
    while isinstance(current, Dictionary) and steps < 200:
        if current.get("/Lang") is not None:
            return True
        current, steps = current.get("/P"), steps + 1
    return pdf is not None and pdf.Root.get("/Lang") is not None


def extract_text_from_element(element: object, keys: Iterable[str]) -> str | None:
    if not isinstance(element, Dictionary):
        return None

    parts: list[str] = []
    for key in keys:
        value = element.get(key)
        if value is not None:
            parts.append(_clean_pdf_text(str(value)))

    text = " ".join(part for part in parts if part)
    return text or None


def extract_text_from_metadata(element: object) -> str | None:
    if not isinstance(element, pikepdf.Stream):
        return extract_text_from_element(element, ["/Title", "/Subject"])

    try:
        raw = element.read_bytes()
    except Exception:
        return None

    return _clean_pdf_text(raw.decode("utf-8", errors="ignore"))


def extract_text_from_page(page_or_element: object) -> str | None:
    # Pages are read through their fonts (the raw letter codes are garbage for many fonts);
    # the raw codes are only a last resort for other content.
    from pdfaccessguru.utils.page_text import page_text

    decoded = page_text(page_or_element)
    if decoded:
        return decoded
    try:
        operations = pikepdf.parse_content_stream(page_or_element)
    except Exception:
        return None

    parts: list[str] = []
    for operands, operator in operations:
        operator_name = str(operator)
        if operator_name in {"Tj", "'", '"'} and operands:
            parts.append(_clean_pdf_text(str(operands[0])))
        elif operator_name == "TJ" and operands:
            for item in operands[0]:
                if isinstance(item, pikepdf.String):
                    parts.append(_clean_pdf_text(str(item)))

    text = " ".join(part for part in parts if part)
    return text or None


def extract_text_from_document(pdf: Pdf) -> str | None:
    parts: list[str] = []
    for page in pdf.pages:
        text = extract_text_from_page(page)
        if text:
            parts.append(text)
        if len(_clean_pdf_text(" ".join(parts))) >= MAX_LANGUAGE_TEXT_LENGTH:
            break

    text = " ".join(parts)
    return text or None


def _normalize_prompt_text(text: str) -> str | None:
    cleaned = _clean_pdf_text(text)
    if not cleaned:
        return None
    return cleaned[:MAX_LANGUAGE_TEXT_LENGTH]


def _strip_response(response: str) -> str:
    return response.strip().strip("`").strip().strip('"').strip("'")


def _clean_pdf_text(text: str) -> str:
    return " ".join(text.replace("\x00", "").split())


def load_available_language_codes() -> list[str]:
    available_locales_path = Path(__file__).resolve().parents[5] / 'LLM' / 'material' / 'availableLocales.json'
    all_language_codes_file_content = open(available_locales_path).read()
    all_language_codes = json.loads(all_language_codes_file_content)['availableLocales']['full']
    return all_language_codes
