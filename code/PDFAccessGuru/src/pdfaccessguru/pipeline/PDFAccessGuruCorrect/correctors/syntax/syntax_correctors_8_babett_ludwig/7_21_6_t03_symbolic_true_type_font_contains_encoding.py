from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_debug


@corrector("symbolic-true-type-font-contains-encoding")
def correct_symbolic_true_type_font_contains_encoding(
    detected_violation: DetectedViolation,
    pdf: Pdf,
) -> Pdf:
    """Removes the invalid '/Encoding' key from a symbolic TrueType font dictionary to satisfy VeraPDF rule 7.21.6-3."""
    font_dict = detected_violation.affected_element
    report_debug(f"font {font_dict}")

    if not isinstance(font_dict, (dict, Dictionary)):
        raise CouldNotCorrectDetectedViolationException(
            "Affected element is not a dictionary – cannot remove /Encoding."
        )

    try:
        del font_dict["/Encoding"]
    except KeyError:
        pass

    #print("corrected font: ", font_dict)

    return pdf