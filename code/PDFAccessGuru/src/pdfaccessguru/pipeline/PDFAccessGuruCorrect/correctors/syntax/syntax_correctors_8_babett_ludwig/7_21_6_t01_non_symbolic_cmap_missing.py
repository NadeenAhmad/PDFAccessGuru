from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_info
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.programs import add_unicode_cmap


@corrector("non-symbolic-cmap-missing")
def correct_non_symbolic_cmap_missing(detected_violation: DetectedViolation, pdf: Pdf) -> None:
    """
    VeraPdf rule_id: 7.21.6-1
    Violation: a non-symbolic TrueType font has no Unicode (3,1) or Mac (1,0) character table.

    Fix (see font_repair/programs.py): a (3,1) table is added that maps every character to the
    glyph viewers show today. The first version mapped characters to glyphs by their position
    in the font, i.e. to the wrong glyphs.
    """
    result = add_unicode_cmap(pdf)
    if result.fixed:
        report_info(f"Character tables added to these fonts: {', '.join(result.fixed)}.")
    if not result.fixed and result.skipped:
        raise CouldNotCorrectDetectedViolationException("; ".join(f"{n}: {r}" for n, r in result.skipped))
