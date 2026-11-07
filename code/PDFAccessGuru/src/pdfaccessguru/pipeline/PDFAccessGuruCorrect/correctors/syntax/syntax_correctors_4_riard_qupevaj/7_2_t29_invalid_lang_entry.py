from pikepdf import Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.utils import normalize_or_set_language


@corrector("invalid-lang-entry")
def correct_invalid_lang_entry(detected_violation: DetectedViolation, pdf: Pdf):
    """VeraPdf rule_id: 7.2-29"""
    normalize_or_set_language(detected_violation.affected_element, pdf, "invalid-lang-entry")
