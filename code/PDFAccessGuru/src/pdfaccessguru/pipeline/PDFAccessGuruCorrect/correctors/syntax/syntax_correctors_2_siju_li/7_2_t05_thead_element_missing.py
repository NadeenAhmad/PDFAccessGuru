from pikepdf import Name, Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import correct_table_section_missing


@corrector("thead-element-missing")
def correct_thead_element_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-5
    """
    correct_table_section_missing(detected_violation, pdf, Name('/THead'), "thead-element-missing")
