from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_info
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.programs import match_widths


@corrector("glyph-width-inconsistent")
def correct_glyph_width_inconsistent(detected_violation: DetectedViolation, pdf: Pdf) -> None:
    """
    VeraPdf rule_id: 7.21.5-1
    Violation: the widths written in the PDF differ from the widths in the embedded font.

    Fix (all TrueType fonts at once, see font_repair/programs.py): the font program gets the
    widths written in the PDF. Those decide where text is placed, so nothing moves. The first
    version changed the PDF widths instead, which shifts text.
    """
    result = match_widths(pdf)
    if result.fixed:
        report_info(f"Character widths inside these fonts now match the file: {', '.join(result.fixed)}.")
    if not result.fixed and result.skipped:
        details = "; ".join(f"{name}: {reason}" for name, reason in result.skipped)
        raise CouldNotCorrectDetectedViolationException(details)
