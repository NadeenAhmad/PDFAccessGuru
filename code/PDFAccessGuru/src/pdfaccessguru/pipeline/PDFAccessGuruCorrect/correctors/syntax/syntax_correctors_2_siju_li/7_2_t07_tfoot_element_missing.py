from pikepdf import Name, Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import correct_table_section_missing


@corrector("tfoot-element-missing")
def correct_tfoot_element_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-7
    Violation: TFoot is not a direct child of Table.

    Fix: Find the Table ancestor and move the TFoot directly under it.
    (Until 2026-11 this corrector passed /THead by mistake.)
    """
    correct_table_section_missing(
        detected_violation,
        pdf,
        Name('/TFoot'),
        "tfoot-element-missing"
    )
