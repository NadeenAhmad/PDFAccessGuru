from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_info
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.programs import add_symbol_cmap


@corrector("embedded-font-program-multiple-cmap-subtables")
def correct_embedded_font_program_multiple_cmap_subtables(detected_violation: DetectedViolation, pdf: Pdf) -> None:
    """
    VeraPdf rule_id: 7.21.6-4
    Violation: a symbolic TrueType font has several character tables but not the Microsoft
    Symbol (3,0) table.

    Fix (see font_repair/programs.py): a (3,0) table is added with the glyphs viewers show today;
    no table is removed. The first version removed tables, which can change the glyphs shown.
    """
    result = add_symbol_cmap(pdf)
    if result.fixed:
        report_info(f"Symbol character tables added to these fonts: {', '.join(result.fixed)}.")
    if not result.fixed and result.skipped:
        raise CouldNotCorrectDetectedViolationException("; ".join(f"{n}: {r}" for n, r in result.skipped))
