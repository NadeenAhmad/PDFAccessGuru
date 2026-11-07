import json
import os
from pathlib import Path
from pikepdf import Dictionary, String
import pikepdf

from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.utils import normalize_lang_tag
from pdfaccessguru.pipeline.reporting.writer import report_review

MAX_ACTUAL_TEXT_LENGTH = 800
DEFAULT_LANGUAGE_CODE = "en-US"
LANG_KEY = '/Lang'


@corrector("natural-language-actual-text-attribute-undefined")
def correct_natural_language_actual_text_attribute_undefined(detected_violation: DetectedViolation, pdf: pikepdf.Pdf):
    """
    VeraPdf rule_id: 7.2-21
    Description: A structure element carries an /ActualText value, but the document
    provides no fallback natural language. veraPDF requires a document level language,
    i.e. a /Lang entry in the catalog (/Root), as the fallback. The affected element's
    own /ActualText is only a replacement text and does not satisfy the rule.

    Fix:
    Ensure the catalog (/Root) has a valid /Lang entry. If the /ActualText of the
    affected element carries meaningful natural language, an LLM maps it to a language
    code; otherwise (empty, whitespace-only, soft hyphen, too long, or when the affected
    element is not a dictionary) a default language code is used.
    The determined code is written to /Root/Lang (and, when possible, to the element).
    """
    if _has_non_empty_lang(pdf.Root):
        return

    language_code = _determine_language_code(detected_violation.affected_element)

    pdf.Root[LANG_KEY] = String(language_code)

    element_obj = detected_violation.affected_element
    if isinstance(element_obj, Dictionary) and not _has_non_empty_lang(element_obj):
        element_obj[LANG_KEY] = String(language_code)


def _has_non_empty_lang(element: object) -> bool:
    """
    Returns True if the given element is a dictionary that carries a non-empty /Lang entry.
    """
    if not isinstance(element, Dictionary):
        return False
    lang = element.get(LANG_KEY)
    return lang is not None and str(lang) != ""


def _determine_language_code(element: object) -> str:
    """
    Determines a language code for the affected element.

    Uses the LLM based language detection only when the affected element is a
    dictionary carrying meaningful /ActualText. In every other case (non-dictionary
    element such as a marked-content id, missing/empty/whitespace-only /ActualText,
    or /ActualText longer than {@link MAX_ACTUAL_TEXT_LENGTH}) the default language
    code {@link DEFAULT_LANGUAGE_CODE} is returned.
    """
    actual_text = element.get('/ActualText') if isinstance(element, Dictionary) else None
    actual_text_str = str(actual_text) if actual_text is not None else ""
    if not _is_meaningful_text(actual_text_str) or len(actual_text_str) > MAX_ACTUAL_TEXT_LENGTH:
        return _default_language_code()

    try:
        reply = prompt_determine_lang_tag(actual_text_str)
    except Exception:
        return _default_language_code()

    # The model's reply is only used if it is a valid language tag (it may come with quotes).
    language_code = normalize_lang_tag(str(reply).strip().strip('"').strip("'"))
    if language_code is None:
        return _default_language_code()
    report_review(f"The document language was set to '{language_code}' by a language model from a single /ActualText. Please check it.")
    return language_code


def _default_language_code() -> str:
    report_review(f"The document language could not be determined and was set to the default '{DEFAULT_LANGUAGE_CODE}'. Please check it.")
    return DEFAULT_LANGUAGE_CODE


def _is_meaningful_text(text: str) -> bool:
    """
    Returns True if the text carries characters usable for natural language detection.

    Strips whitespace and soft hyphens (U+00AD); text that is empty afterwards
    (e.g. the soft hyphen or line break markers found on hyphenation spans) is not
    meaningful for language detection.
    """
    return text.replace('\u00ad', '').strip() != ""


def prompt_determine_lang_tag(actual_text: str) -> str:
    """
    Sends some prompt to some OpenRouterBaseProvider to determine the language code of the actual text.

    Requires that actual_text != "" and len(actual_text) <= {@link MAX_ACTUAL_TEXT_LENGTH}.

    Arguments:
        actual_text: The actual text to determine the language code for. 

    Raises:
        ValueError: If actual_text is empty or actual_text is longer than {@link MAX_ACTUAL_TEXT_LENGTH} characters.
    """
    if actual_text == "":
        raise ValueError("Provided argument actual_text is empty.")
    if len(actual_text) > MAX_ACTUAL_TEXT_LENGTH:
        raise ValueError(f"Provided argument actual_text is longer than {MAX_ACTUAL_TEXT_LENGTH} characters.")

    provider = OpenRouterBaseProvider()
    system_prompt, user_prompt = build_prompt_determine_lang_tag(actual_text)
    return provider.send_message(system_prompt, user_prompt)


def build_prompt_determine_lang_tag(actual_text: str) -> tuple[str, str]:
    """
    Builds the system and user prompts for the prompt_determine_lang_tag function.
    Does it by reading the availableLocales.json file and the 
    prompts/determine_lang_tag_system_prompt.txt and prompts/determine_lang_tag_user_prompt.txt files.
    Placeholders are replaced with the actual values.
    """
    available_locales_path = Path(__file__).resolve().parents[5] / 'LLM' / 'material' / 'availableLocales.json'
    all_language_codes_file_content = open(available_locales_path).read()
    all_language_codes = json.loads(all_language_codes_file_content)['availableLocales']

    system_prompt = open(os.path.join(os.path.dirname(__file__), 'prompts', 'determine_lang_tag_system_prompt.txt')).read()
    system_prompt = system_prompt.replace("{{LANGUAGE_CODES}}", str(all_language_codes))


    user_prompt = open(os.path.join(os.path.dirname(__file__), 'prompts', 'determine_lang_tag_user_prompt.txt')).read()
    user_prompt = user_prompt.replace("{{ACTUAL_TEXT}}", str(actual_text))

    return (system_prompt, user_prompt)
