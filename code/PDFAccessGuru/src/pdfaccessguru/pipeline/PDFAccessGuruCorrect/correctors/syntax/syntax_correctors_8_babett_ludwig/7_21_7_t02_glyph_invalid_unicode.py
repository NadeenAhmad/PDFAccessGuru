import re

from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_debug, report_review

MAX_STREAM_LENGTH = 20000


def parse_llm_corrected_mappings(llm_output: str):
    """Parses hex mapping pairs from the LLM text output into a list of source-to-destination dictionaries."""
    mappings = []

    for src, dst in re.findall(
        r"(<[0-9A-Fa-f]+>)\s*(<[0-9A-Fa-f]+>)", llm_output
    ):
        mappings.append({"src": src, "dst": dst})

    return mappings


def validate_corrected_mappings(wrong_Mappings, corrected_Mappings):
    """Validates that the LLM output maintains the exact quantity and sequence of source glyph hex keys relative to the original faulty mappings."""
    if len(wrong_Mappings) != len(corrected_Mappings):
        return False

    for wrong, corrected in zip(wrong_Mappings, corrected_Mappings):
        if wrong["src"].lower() != corrected["src"].lower():
            return False

    return True


def replace_unicode_mappings(to_unicode_text: str, corrected_Mappings):
    """Replaces faulty character mappings within the raw PostScript ToUnicode CMap text with their corrected Unicode values."""
    corrected_dict = {
        m["src"].lower(): m["dst"] for m in corrected_Mappings
    }

    def replace(match):
        src = match.group(1)
        dst = match.group(2)

        key = f"<{src.lower()}>"

        if key in corrected_dict:
            return f"<{src}> {corrected_dict[key]}"

        return match.group(0)

    result = re.sub(
        r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>",
        replace,
        to_unicode_text,
    )

    return result


def create_space_fallback_mappings(wrong_Mappings):
    """Generates a fallback mapping list replacing every faulty destination character code with a standard space character (<0020>)."""
    return [
        {"src": mapping["src"], "dst": "<0020>"}
        for mapping in wrong_Mappings
    ]


def _plausible_mapping(destination: str) -> bool:
    """A proposed destination like <0041> (one character) that is a plausible character for a document."""
    from pdfaccessguru.LLM.output_checks import plausible_character

    digits = destination.strip("<>")
    if len(digits) not in (4, 6) or not re.fullmatch(r"[0-9A-Fa-f]+", digits):
        return False
    return plausible_character(int(digits, 16))


def _debug_print(*_args, **_kwargs) -> None:
    """Debug output was printed to the user's console; it is dropped (Phase 5)."""


@corrector("glyph-invalid-unicode")
def correct_glyph_invalid_unicode(
    detected_violation: DetectedViolation, pdf: Pdf
):
    """Fixes invalid Unicode mappings in a PDF font's /ToUnicode stream (VeraPDF rule 7.21.7-2) by extracting the CMap stream, querying an LLM to infer the corrected character mapping, falling back to space replacement (<0020>) on failure, and updating the stream."""
    _debug_print("im corrector 7.21.2")
    report_debug("im corrector ")

    toUnicode = detected_violation.affected_element
    _debug_print("to Unicode ", toUnicode)
    _debug_print(
        "SUPPLEMENTARY INFORMATION:",
        detected_violation.supplementary_information,
    )

    wrong_Mappings = detected_violation.supplementary_information
    report_debug(f"wrong Mappings {wrong_Mappings}")
    _debug_print("Wrong Mappings ", wrong_Mappings)

    if toUnicode is None:
        raise CouldNotCorrectDetectedViolationException(
            "No /ToUnicode stream found"
        )

    try:
        raw_stream = toUnicode.read_bytes()
        to_unicode_text = raw_stream.decode("utf-8", errors="ignore")
        report_debug(f"Original ToUnicode Stream: {to_unicode_text}")
    except Exception as e:
        raise CouldNotCorrectDetectedViolationException(
            f"Cannot read ToUnicode stream: {e}"
        )

    if not to_unicode_text or len(to_unicode_text) > MAX_STREAM_LENGTH:
        raise CouldNotCorrectDetectedViolationException(
            "ToUnicode stream empty or too large"
        )

    from pdfaccessguru.LLM.fallback import ai_available, note_fallback
    if not ai_available():
        note_fallback("unicode")
        raise CouldNotCorrectDetectedViolationException(
            "glyph-invalid-unicode: the right characters can only be worked out with an AI model")

    provider = OpenRouterBaseProvider()
    system_prompt, user_prompt = build_prompt_glyph_invalid_unicode(
        to_unicode_text, wrong_Mappings, detected_violation
    )

    try:
        corrected_output = provider.send_message(
            system_prompt, user_prompt
        )

        corrected_Mappings = parse_llm_corrected_mappings(
            corrected_output
        )

        if not validate_corrected_mappings(
            wrong_Mappings, corrected_Mappings
        ):
            raise ValueError("Invalid LLM output")
        # 1.1: keep only proposals that are plausible characters; the others stay as they are (still reported)
        corrected_Mappings = [mapping for mapping in corrected_Mappings if _plausible_mapping(mapping["dst"])]
        if not corrected_Mappings:
            raise ValueError("no plausible character proposed")

    except Exception as e:
        # No space fallback: mapping characters to spaces would silently change the
        # text that screen readers read. The violation stays and is reported.
        raise CouldNotCorrectDetectedViolationException(
            f"glyph-invalid-unicode: no reliable replacement for the invalid Unicode mappings ({e})"
        ) from e

    report_review(
        f"{len(corrected_Mappings)} Unicode mapping(s) of a font were corrected by a language model. Please check the text."
    )

    corrected_to_unicode = replace_unicode_mappings(
        to_unicode_text, corrected_Mappings
    )
    toUnicode.write(corrected_to_unicode.encode("utf-8"))


def build_prompt_glyph_invalid_unicode(
    to_unicode_text: str, wrong_Mappings, detected_violation
):
    """Constructs system and user prompts to query an LLM for fixing invalid /ToUnicode character mappings."""
    system_prompt = """
You are a PDF expert fixing PDF/UA-1 ToUnicode CMap errors.

Task:
- Correct the given invalid Unicode mappings.
- Use the ToUnicode CMap Stream to determine the intended character.
- The detected violation describes the PDF/UA-1 rule that must be fixed.

Rules:
- Keep the original glyph source codes unchanged.
- Return one corrected mapping for each invalid mapping.
- Keep the same order as the input mappings.
- If there is any uncertainty, ambiguity, or insufficient evidence, ALWAYS use U+0020 (space).
Do not guess characters.
A wrong semantic character is worse than a space.
- Output only mappings, no explanations.

Format:
<src> <correct_unicode_hex>

Example:
<01> <0041>
<02> <0020>
"""

    wrong_mappings_text = "\n".join(
        f"{mapping['src']} {mapping['dst']} ({mapping['unicode']})"
        for mapping in wrong_Mappings
    )

    user_prompt = f"""
PDF/UA-1 violation:
{detected_violation}

Invalid mappings:
{wrong_mappings_text}

ToUnicode CMap:
{to_unicode_text}


Return the corrected mappings in the same order.
"""

    return system_prompt, user_prompt