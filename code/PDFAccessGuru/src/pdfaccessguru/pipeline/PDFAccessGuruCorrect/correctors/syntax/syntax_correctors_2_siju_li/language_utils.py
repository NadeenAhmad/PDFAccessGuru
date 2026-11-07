import json
from pathlib import Path
from typing import Iterable

import pikepdf
from pikepdf import Dictionary, Name, Pdf, String

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    DEFAULT_LANG,
    normalize_lang_tag,
    normalize_children_of_element,
    find_language,
)

MAX_LANGUAGE_TEXT_LENGTH = 800

# for 7.2-2
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
    """Same order as the shared helper: word statistics, then the AI, then the surroundings."""
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.language_utils import (
        choose_language_for_text as choose,
    )
    return choose(text, pdf, element)


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


def extract_text_for_struct_element(element: object) -> str | None:
    """
    Extract the text belonging to a structure element by resolving its
    (possibly nested) marked-content references against the actual page
    content stream(s). Needed for struct elements that have no own content
    stream (e.g. Table children like TR/TH/TD), where text lives on the
    page and is only linked via MCID.
    """
    if not isinstance(element, Dictionary):
        return None

    refs, _ = _collect_marked_content_refs(element)
    if not refs:
        return None

    refs_by_page: dict[tuple, set[int]] = {}
    page_lookup: dict[tuple, Dictionary] = {}
    for page, mcid in refs:
        key = page.objgen
        refs_by_page.setdefault(key, set()).add(mcid)
        page_lookup[key] = page

    parts: list[str] = []
    for key, mcids in refs_by_page.items():
        parts.append(_extract_text_for_mcids(page_lookup[key], mcids))

    text = " ".join(part for part in parts if part)
    return text or None


def _collect_marked_content_refs(
    element: Dictionary, inherited_page: object | None = None
) -> tuple[list[tuple], list]:
    """Recursively collect (page, mcid) pairs and /OBJR object refs in a struct subtree."""
    refs: list[tuple] = []
    obj_refs: list = []

    page = element.get("/Pg") or inherited_page
    kids = normalize_children_of_element(element)

    for kid in kids:
        if isinstance(kid, int):
            if page is not None:
                refs.append((page, kid))
        elif isinstance(kid, Dictionary):
            kid_type = str(kid.get("/Type", "")).lstrip("/")
            if kid_type == "MCR":
                kid_page = kid.get("/Pg") or page
                mcid = kid.get("/MCID")
                if kid_page is not None and mcid is not None:
                    refs.append((kid_page, int(mcid)))
            elif kid_type == "OBJR":
                obj = kid.get("/Obj")
                if obj is not None:
                    obj_refs.append(obj)
            else:
                sub_refs, sub_obj_refs = _collect_marked_content_refs(kid, page)
                refs.extend(sub_refs)
                obj_refs.extend(sub_obj_refs)

    return refs, obj_refs


def _extract_text_for_mcids(page: Dictionary, wanted_mcids: set[int]) -> str:
    resources = page.get("/Resources") or {}
    properties = resources.get("/Properties") if isinstance(resources, Dictionary) else None

    parts: list[str] = []
    mc_stack: list[int | None] = []

    try:
        operations = pikepdf.parse_content_stream(page)
    except Exception:
        return ""

    for operands, operator in operations:
        op_name = str(operator)

        if op_name == "BDC":
            mcid = _resolve_mcid(operands, properties)
            mc_stack.append(mcid if mcid in wanted_mcids else None)
        elif op_name == "BMC":
            mc_stack.append(None)
        elif op_name == "EMC":
            if mc_stack:
                mc_stack.pop()
        elif mc_stack and mc_stack[-1] is not None:
            if op_name in {"Tj", "'", '"'} and operands:
                parts.append(_clean_pdf_text(str(operands[-1])))
            elif op_name == "TJ" and operands:
                for item in operands[0]:
                    if isinstance(item, pikepdf.String):
                        parts.append(_clean_pdf_text(str(item)))

    return " ".join(part for part in parts if part)


def _resolve_mcid(operands, properties: Dictionary | None) -> int | None:
    if len(operands) < 2:
        return None
    props = operands[1]
    if isinstance(props, Dictionary):
        mcid = props.get("/MCID")
        return int(mcid) if mcid is not None else None
    if isinstance(props, Name) and properties is not None:
        prop_dict = properties.get(str(props))
        if isinstance(prop_dict, Dictionary):
            mcid = prop_dict.get("/MCID")
            return int(mcid) if mcid is not None else None
    return None


def _normalize_prompt_text(text: str) -> str | None:
    cleaned = _clean_pdf_text(text)
    if not cleaned or len(cleaned) > MAX_LANGUAGE_TEXT_LENGTH:
        return None
    return cleaned


def _strip_response(response: str) -> str:
    return response.strip().strip("`").strip().strip('"').strip("'")


def _clean_pdf_text(text: str) -> str:
    return " ".join(text.replace("\x00", "").split())


def load_available_language_codes() -> list[str]:
    available_locales_path = Path(__file__).resolve().parents[5] / 'LLM' / 'material' / 'availableLocales.json'
    all_language_codes_file_content = open(available_locales_path).read()
    all_language_codes = json.loads(all_language_codes_file_content)['availableLocales']['full']
    return all_language_codes