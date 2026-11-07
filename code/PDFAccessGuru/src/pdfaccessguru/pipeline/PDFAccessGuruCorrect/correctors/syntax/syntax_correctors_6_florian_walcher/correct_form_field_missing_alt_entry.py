import io
import fitz  # PyMuPDF
import pikepdf
from pikepdf import Pdf, String
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.pipeline.reporting.writer import report_review


def build_prompt_form_field_tu(field_type_str: str, partial_name: str, page_text: str) -> tuple[str, str]:
    system_prompt = """
You are an expert PDF accessibility corrector (PDF/UA).
Generate a clear screen-reader label for a form field (e.g., "First Name field", "Signature box").
Return ONLY the raw label string (1 to 6 words).
"""
    user_text = f"Field Type: {field_type_str}\nName: {partial_name}\nContext: {page_text[:1000]}"
    return system_prompt, user_text


@corrector("form-field-missing-alt-entry")
def correct_form_field_missing_alt_entry(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.18.1-3
    Injects user-friendly tooltips into interactive form fields.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("Form field is not a valid dictionary.")

    partial_name = str(affected_element.get("/T", ""))
    ft_key = str(affected_element.get("/FT", ""))
    field_type_map = {
        "/Tx": "Text Input",
        "/Btn": "Button",
        "/Ch": "Dropdown Menu",
        "/Sig": "Digital Signature"
    }
    field_type_str = field_type_map.get(ft_key, "Form Field")

    from pdfaccessguru.LLM.fallback import ai_available, note_fallback
    use_ai = ai_available()
    clean_page_text = ""
    try:
        if not use_ai:
            raise RuntimeError("no AI: the page text is not needed")
        pdf_buffer = io.BytesIO()
        pdf.save(pdf_buffer)
        pdf_buffer.seek(0)
        doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
        if len(doc) > 0:
            clean_page_text = doc[0].get_text("text").strip()
    except Exception:
        clean_page_text = ""

    # Multi-stage LLM / Local Fallback
    generated_tu = None
    if use_ai:
        try:
            system_prompt, user_text = build_prompt_form_field_tu(field_type_str, partial_name, clean_page_text)
            generated_tu = OpenRouterBaseProvider().send_message(system_prompt, user_text)
        except Exception:
            generated_tu = None
    else:
        note_fallback("form_field")

    readable_name = _readable_field_name(partial_name)
    if generated_tu and len(generated_tu.strip()) > 0:
        clean_tu = generated_tu.strip().replace("`", "").replace('"', '').replace("'", "")
    elif readable_name:
        clean_tu = f"{field_type_str}: {readable_name}"
    else:
        clean_tu = f"Interactive {field_type_str}"

    affected_element["/TU"] = pikepdf.String(clean_tu)
    report_review(f"Form field description was generated automatically: '{clean_tu}'. Please check it.")


def _readable_field_name(name: str) -> str:
    """'first_name' -> 'First name', 'txtEmailAddress' -> 'Email address', 'Text1' -> ''."""
    import re

    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", name or "")
    words = re.sub(r"[_\-.\[\]0-9]+", " ", words).split()
    if words and words[0].lower() in ("txt", "tb", "fld", "field", "cb", "chk", "rb", "dd", "btn"):
        words = words[1:]
    if not words or (len(words) == 1 and words[0].lower() in ("text", "check", "box", "button", "untitled")):
        return ""
    text = " ".join(words).lower()
    return text[0].upper() + text[1:]
