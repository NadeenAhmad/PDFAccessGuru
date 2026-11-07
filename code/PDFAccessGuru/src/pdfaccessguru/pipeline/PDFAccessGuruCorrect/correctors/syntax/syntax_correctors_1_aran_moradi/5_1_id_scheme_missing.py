from pikepdf import Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi.pdfua_identification import (
    metadata_stream,
    write_pdfua_identification,
)


@corrector("id-schema-missing")
def correct_id_schema_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 5-1
    Violation description: The document metadata stream doesn't contain the PDF/UA Identification Schema
    Correction strategy:
    The PDF/UA identification in the XMP metadata is rewritten as a single
    pdfuaid:part = 1 with the correct prefix (see pdfua_identification.py).
    Other schemas, including the PDF/A identification, are not changed.
    """
    write_pdfua_identification(metadata_stream(pdf, detected_violation.affected_element))
