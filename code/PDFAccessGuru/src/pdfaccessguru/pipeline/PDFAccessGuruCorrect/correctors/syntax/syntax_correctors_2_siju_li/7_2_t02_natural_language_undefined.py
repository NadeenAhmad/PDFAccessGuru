from pikepdf import Pdf, String
import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import normalize_kids
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.utils import normalize_lang_tag
from pdfaccessguru.pipeline.reporting.writer import report_review


@corrector("natural-language-undefined")
def correct_natural_language_undefined(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-2
    Violation: Natural language of Outline entries cannot be determined because
    no /Lang tag is set at document level.

    Fix: Find an existing /Lang entry anywhere in the document and set it at
    Root level. If none exists, fall back to "en-US".

    Before:
        /Root: { ... }   <- no /Lang

    After:
        /Root: { /Lang: "en-US", ... }
    """
    root = pdf.Root

    if '/Lang' in root:
        return

    # Try to find an existing /Lang entry in the structure tree
    def find_lang(node: pikepdf.Object) -> str | None:
        if isinstance(node, pikepdf.Dictionary):
            if '/Lang' in node:
                return str(node['/Lang'])
            for kid in normalize_kids(node):
                result = find_lang(kid)
                if result is not None:
                    return result
        return None

    struct_tree_root = root.get('/StructTreeRoot')
    lang = normalize_lang_tag(find_lang(struct_tree_root)) if struct_tree_root else None

    if lang is None:
        from pdfaccessguru.LLM.fallback import detect_language
        from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.language_utils import (
            extract_text_from_document,
        )
        lang = normalize_lang_tag(detect_language(extract_text_from_document(pdf), min_confidence=0.8))
    if lang is None:
        lang = "en-US"
        report_review("The document language could not be determined and was set to the default 'en-US'. Please check it.")
    root['/Lang'] = String(lang)
