from pikepdf import Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi.pdfua_identification import (
    metadata_stream,
    write_pdfua_identification,
)


@corrector("invalid-part-property")
def correct_invalid_part_property(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 5-2
    Violation description: The "part" property of the PDF/UA Identification Schema is not 1
    Correction strategy:
    The PDF/UA identification in the XMP metadata is rewritten as a single
    pdfuaid:part = 1 with the correct prefix (see pdfua_identification.py).
    Other schemas, including the PDF/A identification, are not changed.
    """
    write_pdfua_identification(metadata_stream(pdf, detected_violation.affected_element))
