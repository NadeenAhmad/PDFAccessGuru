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


def build_prompt_ocg_name(page_text: str) -> tuple[str, str]:
    system_prompt = """
You are an expert PDF accessibility corrector (PDF/UA).
Generate a concise layer name (e.g., "Watermark", "Background Image", "Content Layer").
Return ONLY the raw layer name (1 to 4 words).
"""
    user_text = f"Document Context:\n{page_text[:1000]}"
    return system_prompt, user_text


@corrector("missing-empty-name")
def correct_missing_empty_name(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.10-1
    Injects valid layer names into Optional Content Groups (OCG).
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("missing-empty-name: Element is not a dictionary.")

    clean_page_text = ""
    try:
        pdf_buffer = io.BytesIO()
        pdf.save(pdf_buffer)
        pdf_buffer.seek(0)
        doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
        if len(doc) > 0:
            clean_page_text = doc[0].get_text("text").strip()
    except Exception:
        clean_page_text = ""

    # Multi-stage LLM / Local Fallback
    generated_name = None
    try:
        system_prompt, user_text = build_prompt_ocg_name(clean_page_text)
        generated_name = OpenRouterBaseProvider().send_message(system_prompt, user_text)
    except Exception:
        generated_name = None

    if generated_name and len(generated_name.strip()) > 0:
        clean_name = generated_name.strip().replace("`", "").replace('"', '').replace("'", "")
    else:
        clean_name = "Optional Content Layer"

    affected_element["/Name"] = pikepdf.String(clean_name)
    report_review(f"Optional content (layer) configuration was named automatically: '{clean_name}'. Please check it.")