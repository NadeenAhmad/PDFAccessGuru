import io
import json
import requests
import pymupdf as fitz  # PyMuPDF
import pikepdf
from pikepdf import Pdf
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
import pdfaccessguru.LLM.providers.openrouter_provider as orp

def collect_all_note_elements(node: pikepdf.Dictionary, notes_list: list, visited: set | None = None) -> None:
    """
    Recursively traverses the structure tree (/StructTreeRoot) to collect all /Note
    structure elements in document reading order.
    """
    if visited is None:
        visited = set()

    if not isinstance(node, pikepdf.Dictionary):
        return

    node_ref = node.objgen if hasattr(node, "objgen") else id(node)
    if node_ref in visited:
        return
    visited.add(node_ref)

    # Check if current node is a Note structure tag
    struct_type = str(node.get("/S", ""))
    if struct_type in ["/Note", "Note"]:
        notes_list.append(node)

    # Inspect children (/K)
    if "/K" in node:
        kids = node["/K"]
        if isinstance(kids, pikepdf.Array):
            for child in kids:
                if isinstance(child, pikepdf.Dictionary):
                    collect_all_note_elements(child, notes_list, visited)
        elif isinstance(kids, pikepdf.Dictionary):
            collect_all_note_elements(kids, notes_list, visited)


def build_prompt_note_title(note_id: str, page_text: str) -> tuple[str, str]:
    system_prompt = """
You are an expert PDF accessibility corrector (PDF/UA).

You will receive the sequential note ID (e.g., "note1") and the page text context surrounding a footnote/endnote annotation.

Your task:
1. Generate a concise, user-friendly descriptive title for this footnote/note reference (e.g., "Note 1: Financial year definition" or "Note 2: Methodology source").
2. Return ONLY the final clean title string. Do NOT include markdown formatting, backticks, quotation marks, or explanations.
"""
    user_text = f"""
Note Identifier: {note_id}

Document Page Text Context:
-----------------
{page_text[:2000]}
-----------------

Generate a descriptive title for this note entry.
"""
    return system_prompt, user_text


@corrector("id-note-tag-non-unique")
def correct_id_note_tag_non_unique(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.9-2

    Violation description: A Note structure element shall have an ID entry.

    Correction strategy:
    - Traverse the document structure tree (/StructTreeRoot) to count /Note elements in reading order.
    - Determine the 1-based sequential index of the target note (e.g., note1, note2).
    - Extract page context using PyMuPDF to optionally create a descriptive title.
    - Inject the unique sequential string into the /ID attribute (and optional /Title) in-place.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("id-note-tag-non-unique: Affected element is not a valid dictionary structure.")

    # 1. Collect all /Note elements across the document structure tree
    notes_list = []
    if "/StructTreeRoot" in pdf.Root:
        struct_tree_root = pdf.Root["/StructTreeRoot"]
        if isinstance(struct_tree_root, pikepdf.Dictionary):
            collect_all_note_elements(struct_tree_root, notes_list)

    # 2. Find the 1-based index of affected_element in reading order
    note_index = 1
    target_objgen = affected_element.objgen if hasattr(affected_element, "objgen") else None

    for idx, elem in enumerate(notes_list, start=1):
        elem_objgen = elem.objgen if hasattr(elem, "objgen") else None
        if (target_objgen and elem_objgen == target_objgen) or elem == affected_element:
            note_index = idx
            break

    unique_note_id = f"note{note_index}"

    # 3. Determine zero-based page index for contextual text retrieval
    page_index = 0
    page_obj = affected_element.get("/Pg")
    if page_obj and hasattr(page_obj, "objgen"):
        for idx, page in enumerate(pdf.pages):
            if page.objgen == page_obj.objgen:
                page_index = idx
                break

    # 4. Extract page text context using PyMuPDF
    clean_page_text = ""
    try:
        pdf_buffer = io.BytesIO()
        pdf.save(pdf_buffer)
        pdf_buffer.seek(0)

        doc = fitz.open(stream=pdf_buffer.read(), filetype="pdf")
        if len(doc) > page_index:
            page_text = doc[page_index].get_text("text")
            if isinstance(page_text, str):
                clean_page_text = page_text.strip()
            elif isinstance(page_text, (list, tuple)):
                clean_page_text = "".join(str(part) for part in page_text).strip()
            elif isinstance(page_text, dict):
                clean_page_text = "".join(str(part) for part in page_text.values()).strip()
            else:
                clean_page_text = str(page_text).strip()
    except Exception:
        clean_page_text = ""

    # 5. Generate Descriptive Title (Mock Pathway or Active Multimodal LLM Pathway)
    try:
        system_prompt, user_text = build_prompt_note_title(unique_note_id, clean_page_text)

        generated_title = orp.OpenRouterBaseProvider().send_message(system_prompt, user_text)

        if not generated_title or len(generated_title.strip()) == 0:
            descriptive_title = f"Footnote Reference {note_index}"
        else:
            descriptive_title = generated_title.strip().replace("`", "").replace('"', '').replace("'", "")

    except Exception:
        descriptive_title = f"Footnote Reference {note_index}"

    # 6. Apply required /ID key and optional accessibility /Title key in-place
    affected_element["/ID"] = pikepdf.String(unique_note_id)
    affected_element["/Title"] = pikepdf.String(descriptive_title)