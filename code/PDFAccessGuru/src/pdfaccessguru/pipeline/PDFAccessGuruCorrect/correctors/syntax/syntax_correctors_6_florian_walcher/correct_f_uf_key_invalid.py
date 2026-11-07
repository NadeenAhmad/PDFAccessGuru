import re

import pikepdf
from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_review

_MIME_EXTENSIONS = {
    "application/pdf": "pdf", "text/csv": "csv", "text/plain": "txt", "application/xml": "xml",
    "text/xml": "xml", "image/png": "png", "image/jpeg": "jpg", "application/zip": "zip",
}


def _mime_type(file_spec: pikepdf.Dictionary) -> str:
    embedded = file_spec.get("/EF")
    if isinstance(embedded, pikepdf.Dictionary):
        for key in ("/F", "/UF"):
            stream = embedded.get(key)
            if isinstance(stream, pikepdf.Stream) and "/Subtype" in stream:
                return str(stream["/Subtype"]).lstrip("/").replace("#2F", "/").lower()
    return ""


@corrector("f-uf-key-invalid")
def correct_f_uf_key_invalid(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.11-1
    Violation description: the file specification of an embedded file lacks the /F or /UF key.

    Correction strategy:
    The file name that is present (/UF, else /F) is copied into the missing key. Existing
    names are never changed. Only if neither key exists, a name is derived from /Desc and
    the file's MIME type (or "attachment"), and it is reported for review.
    """
    file_spec = detected_violation.affected_element
    if not isinstance(file_spec, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("f-uf-key-invalid: element is not a dictionary")

    existing = file_spec.get("/UF") or file_spec.get("/F")
    if existing is not None and str(existing).strip():
        name = str(existing)
    else:
        stem = re.sub(r"[^\w.-]+", "_", str(file_spec.get("/Desc", "")).strip()).strip("_") or "attachment"
        extension = _MIME_EXTENSIONS.get(_mime_type(file_spec))
        name = f"{stem}.{extension}" if extension and not stem.endswith(f".{extension}") else stem
        report_review(f"An embedded file had no name; it was named '{name}'. Please enter the real file name.")

    if "/F" not in file_spec or not str(file_spec.get("/F")).strip():
        file_spec["/F"] = pikepdf.String(name)
    if "/UF" not in file_spec or not str(file_spec.get("/UF")).strip():
        file_spec["/UF"] = pikepdf.String(name)
