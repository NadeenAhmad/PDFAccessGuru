from pikepdf import Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.language_utils import (
    choose_language_for_text,
    extract_text_from_element,
)
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.utils import (
    has_valid_language,
    set_language_value,
)


@corrector("natural-language-tu-form-fields-undefined")
def correct_natural_language_tu_form_fields_undefined(detected_violation: DetectedViolation, pdf: Pdf):
    """VeraPdf rule_id: 7.2-25"""
    affected_element = detected_violation.affected_element
    if has_valid_language(pdf, affected_element):
        return

    text = extract_text_from_element(affected_element, ["/TU"])
    lang = choose_language_for_text(text, pdf, affected_element)
    set_language_value(affected_element, pdf, "natural-language-tu-form-fields-undefined", lang)
