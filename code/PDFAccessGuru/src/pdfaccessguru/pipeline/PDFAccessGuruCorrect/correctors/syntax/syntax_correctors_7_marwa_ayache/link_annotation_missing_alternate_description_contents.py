from pathlib import Path

from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.pipeline.reporting.writer import report_review

from .common import (
    CouldNotCorrectDetectedViolationException,
    DetectedViolation,
    corrector,
    pikepdf,
)

MAX_CONTENTS_LENGTH = 240
VIOLATION_NAME = "link-annotation-missing-alternate-description-contents"


@corrector("link-annotation-missing-alternate-description-contents")
def correct_link_annotation_missing_alternate_description_contents(detected_violation: DetectedViolation, pdf):
    """
    VeraPdf rule_id: 7.18.5-2

    Every link without a description gets one, for the whole document at once (see
    correctors/descriptions/links.py): its visible text plus where it goes, e.g.
    "Annual report 2023 (link to example.com/report)" or "Link to page 5". This needs no AI and
    is exact. The AI is asked only for links with neither visible text nor a readable target;
    without an AI those get the word "Link" and are listed for checking.
    """
    from pdfaccessguru.LLM.fallback import ai_available, note_fallback
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.links import describe_links
    from pdfaccessguru.pipeline.reporting.writer import report_info

    def ask_ai(annotation, page_number: int) -> str | None:
        if not ai_available():
            return None
        try:
            return prompt_link_annotation_contents(annotation) or None
        except Exception:
            return None

    result = describe_links(pdf, ask_ai=ask_ai)
    if result.described:
        report_info(f"{result.described} link(s) got a description from their visible text and target.")
    if result.by_ai:
        report_review(f"{result.by_ai} link description(s) were written by an AI model. Please check them.")
    if result.generic:
        if not ai_available():
            note_fallback("link_text")
        report_review(f"{result.generic} link(s) have neither visible text nor a readable target; "
                      "they were described only as 'Link'. Please add a better description.")


def prompt_link_annotation_contents(link_annotation) -> str:
    """
    Ask the configured OpenRouter provider for the missing /Contents value.

    The response is sanitized because this value is written directly into the
    PDF annotation dictionary.
    """
    system_prompt, user_prompt = build_prompt_link_annotation_contents(link_annotation)
    response = OpenRouterBaseProvider().send_message(system_prompt, user_prompt)
    contents = _sanitize_contents_response(response)

    if not contents:
        raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)

    return contents


def build_prompt_link_annotation_contents(link_annotation) -> tuple[str, str]:
    """
    Build a role-play prompt pair for generating a link annotation /Contents value.
    """
    prompt_dir = Path(__file__).with_name("prompts")
    system_prompt = (prompt_dir / "link_annotation_contents_system_prompt.txt").read_text(encoding="utf-8")
    user_prompt_template = (prompt_dir / "link_annotation_contents_user_prompt.txt").read_text(encoding="utf-8")

    user_prompt = user_prompt_template.replace(
        "{{LINK_ANNOTATION_CONTEXT}}",
        _build_link_annotation_context(link_annotation),
    )

    return system_prompt, user_prompt


def _build_link_annotation_context(link_annotation) -> str:
    fields = {
        "Subtype": link_annotation.get("/Subtype"),
        "Rect": link_annotation.get("/Rect"),
        "Destination": link_annotation.get("/Dest"),
        "Action": link_annotation.get("/A"),
        "Existing Contents": link_annotation.get("/Contents"),
        "StructParent": link_annotation.get("/StructParent"),
    }
    lines = []

    for label, value in fields.items():
        if value is not None:
            lines.append(f"{label}: {_stringify_pdf_value(value)}")

    return "\n".join(lines) if lines else "No additional link annotation context is available."


def _stringify_pdf_value(value: object) -> str:
    return str(value)


def _sanitize_contents_response(response: str) -> str:
    contents = response.strip().strip('"').strip("'").strip()
    contents = " ".join(contents.split())

    if not contents:
        return ""

    return contents[:MAX_CONTENTS_LENGTH].rstrip()
