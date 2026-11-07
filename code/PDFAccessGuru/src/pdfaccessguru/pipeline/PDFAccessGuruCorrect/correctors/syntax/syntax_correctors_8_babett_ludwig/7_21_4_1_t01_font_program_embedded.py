from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_info
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.embed import embed_missing_fonts


@corrector("font-program-embedded")
def correct_font_program_embedded(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.21.4.1-1
    Violation: a font that is used for text is not embedded in the file.

    Fix (all fonts of the document at once, see font_repair/embed.py): the same font from this
    computer is embedded if its licence allows it; for Arial/Helvetica, Times New Roman/Times
    and Courier New/Courier a free font with identical letter widths (Liberation) is used
    otherwise. The character widths in the PDF are kept, so every character stays exactly where
    it is (the pipeline checks this). The first version replaced every font with one sans-serif
    font and recomputed the widths, which moved text.
    """
    result = embed_missing_fonts(pdf)
    if result.embedded:
        report_info(f"Fonts added to the file: {', '.join(result.embedded)}.")
    for name, look_alike in result.look_alikes:
        report_info(f"{name} is not on this computer, so a free font with the same letter widths was used ({look_alike}).")
    if result.skipped:
        details = "; ".join(f"{name}: {reason}" for name, reason in result.skipped)
        if not result.embedded:
            raise CouldNotCorrectDetectedViolationException(f"No font could be added. {details}")
        report_info(f"Fonts that could not be added: {details}.")
