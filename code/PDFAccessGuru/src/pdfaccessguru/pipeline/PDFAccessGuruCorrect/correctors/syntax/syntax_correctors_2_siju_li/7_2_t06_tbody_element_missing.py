from pikepdf import Name, Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import correct_table_section_missing


@corrector("tbody-element-missing")
def correct_tbody_element_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-6
    """
    correct_table_section_missing(detected_violation, pdf, Name('/TBody'), "tbody-element-missing")
