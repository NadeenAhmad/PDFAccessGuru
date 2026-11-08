import io
import pymupdf as fitz  # PyMuPDF
import pikepdf
from pikepdf import Pdf, String
from pdfaccessguru.model.LLM.image import Image
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.pipeline.reporting.writer import report_review


def build_prompt_multimodal_formula(has_bbox: bool, page_text: str = "") -> tuple[str, str]:
    if has_bbox:
        system_prompt = """
You are an expert PDF accessibility corrector specializing in PDF/UA standards.
You will receive a visual image snippet containing a mathematical formula cropped directly from a document page.

Your task:
1. Visually transcribe the mathematical formula shown in the attached image.
2. Convert it into a clean, concise, natural-language description suitable for a screen-reader (e.g., "E equals m c squared" or "the integral from a to b of f of x dx").
3. Return ONLY the final raw description string. Do not include markdown tags, backticks, conversational preamble, or explanations.
"""
        user_text = "Please analyze the attached cropped image and generate its mathematical alternative text entry."
    else:
        system_prompt = """
You are an expert PDF accessibility corrector specializing in PDF/UA standards.
You will receive an image of an ENTIRE document page, along with the extracted text context of that page. Somewhere on this page is a mathematical formula tagged for accessibility that currently lacks an alternative text description.

Your task:
1. Scan the page image and locate the mathematical formula or equation. Use the provided page text context to help identify its location or meaning if necessary.
2. Convert the formula into a clean, concise, natural-language description suitable for a screen-reader (e.g., "y equals mx plus c" or "the summation from i equals 1 to n").
3. Return ONLY the final raw description string. Do not include markdown tags, backticks, conversational preamble, or explanations.
"""
        user_text = f"""
Page Text Context to locate/identify the equation:
-----------------
{page_text[:2500]}
-----------------

Please analyze the full page image, locate the formula, and generate its screen-reader friendly alternative text entry.
"""
    return system_prompt, user_text


@corrector("formula-structure-no-alternative-description")
def correct_formula_structure_no_alternative_description(detected_violation: DetectedViolation, pdf: Pdf) -> None:
    """
    VeraPdf rule_id: 7.7-1

    Dual-Pathway Visual Strategy with multi-stage fallbacks:
    - Discover explicit formula layout coordinates (/BBox).
    - Extract a high-DPI visual crop or full page render into raw PNG bytes.
    - Execute vision API request with graceful fallbacks to text LLM and local context.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("Formula element context is not a valid structure dictionary.")

    # 1. Look for a Bounding Box (/BBox) attribute array
    bbox = None
    if "/A" in affected_element:
        attribs = affected_element["/A"]
        if isinstance(attribs, pikepdf.Array):
            for item in attribs:
                if isinstance(item, pikepdf.Dictionary) and "/BBox" in item:
                    bbox = [float(n) for n in item["/BBox"]]
                    break
        elif isinstance(attribs, pikepdf.Dictionary) and "/BBox" in attribs:
            bbox = [float(n) for n in attribs["/BBox"]]

    # 2. Determine zero-based page index using /Pg
    page_index = 0
    pg_obj = affected_element.get("/Pg")
    if pg_obj and hasattr(pg_obj, "objgen"):
        for idx, page in enumerate(pdf.pages):
            if page.objgen == pg_obj.objgen:
                page_index = idx
                break

    page_text_context = ""
    raw_png_bytes = None

    try:
        pdf_buffer = io.BytesIO()
        pdf.save(pdf_buffer)
        pdf_buffer.seek(0)
        
        doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
        if len(doc) > page_index:
            page = doc[page_index]

            if bbox:
                page_height = page.rect.height
                pk_x0, pk_y0, pk_x1, pk_y1 = bbox
                fz_x0 = pk_x0
                fz_y0 = page_height - pk_y1
                fz_x1 = pk_x1
                fz_y1 = page_height - pk_y0

                crop_rect = fitz.Rect(fz_x0 - 4, fz_y0 - 4, fz_x1 + 4, fz_y1 + 4)
                zoom_matrix = fitz.Matrix(3.0, 3.0)
                pixmap = page.get_pixmap(matrix=zoom_matrix, clip=crop_rect)
            else:
                try:
                    extracted_text = page.get_text("text")
                    page_text_context = extracted_text.strip() if isinstance(extracted_text, str) else ""
                except Exception:
                    page_text_context = ""
                    
                zoom_matrix = fitz.Matrix(1.5, 1.5)
                pixmap = page.get_pixmap(matrix=zoom_matrix)
                
            raw_png_bytes = pixmap.tobytes("png")

    except Exception as e:
        raise CouldNotCorrectDetectedViolationException(f"Failed to generate layout image snapshot: {e}")

    # 3. Multi-stage LLM / Fallback sequence
    has_bbox = bbox is not None
    system_prompt, user_text = build_prompt_multimodal_formula(has_bbox, page_text_context)
    from pdfaccessguru.LLM.fallback import ai_available, note_fallback
    use_ai = ai_available()
    provider = OpenRouterBaseProvider()
    generated_alt_text = None
    if not use_ai:
        note_fallback("formula")

    # Attempt 1: Vision LLM call
    if use_ai and raw_png_bytes:
        try:
            image_obj = Image(raw_png_bytes)
            generated_alt_text = provider.send_message_with_image(system_prompt, user_text, image_obj)
        except Exception:
            generated_alt_text = None

    # Attempt 2: Text LLM call (fallback if vision call fails or hits 401)
    if use_ai and not generated_alt_text:
        try:
            generated_alt_text = provider.send_message(system_prompt, user_text)
        except Exception:
            generated_alt_text = None

    # Attempt 3: Local context fallback (guarantees execution completion)
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.layout import Layout
    own_text = " ".join((Layout(pdf).text(affected_element) or "").split())[:200]
    if generated_alt_text and len(generated_alt_text.strip()) > 0:
        clean_text = generated_alt_text.strip().replace("`", "").replace('"', '').replace("'", "")
    elif len(own_text) >= 2:
        clean_text = f"Formula: {own_text}"                 # the formula's own text, read aloud
    elif page_text_context:
        first_words = " ".join(page_text_context.split()[:5])
        clean_text = f"Mathematical formula near: '{first_words}...'"
    else:
        clean_text = "Mathematical formula expression"

    # 4. Inject description directly into structural element
    affected_element["/Alt"] = pikepdf.String(clean_text)
    report_review(
        f"Formula description was generated automatically: '{clean_text}'. Please check it.",
        context=("Nearby text: " + " ".join(page_text_context.split())[:300]) if page_text_context else None,
        image_png=raw_png_bytes if "raw_png_bytes" in locals() and isinstance(raw_png_bytes, bytes) else None,
    )