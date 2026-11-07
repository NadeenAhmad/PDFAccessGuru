from pikepdf import Name, Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


@corrector("invalid-non-symbolic-font-Adobe-mapping")
def correct_invalid_non_symbolic_font_Adobe_mapping(
    detected_violation: DetectedViolation,
    pdf: Pdf,
) -> None:
    """Ensures a non-symbolic TrueType font uses a valid standard Adobe encoding mapping by setting or updating its BaseEncoding to WinAnsiEncoding and removing conflicting Differences arrays."""
    font = detected_violation.affected_element

    if font.get("/Subtype") != Name("/TrueType"):
        return

    descriptor = font.get("/FontDescriptor")
    if descriptor is None:
        return

    flags = descriptor.get("/Flags", 0)
    is_symbolic = bool(flags & 4)

    if is_symbolic:
        return

    encoding = font.get("/Encoding")

    if encoding == Name("/Identity-H"):
        font["/Encoding"] = Name("/WinAnsiEncoding")

    elif isinstance(encoding, dict):
        base_encoding = encoding.get("/BaseEncoding")

        if base_encoding not in [
            Name("/MacRomanEncoding"),
            Name("/WinAnsiEncoding"),
        ]:
            encoding["/BaseEncoding"] = Name("/WinAnsiEncoding")

        if "/Differences" in encoding:
            del encoding["/Differences"]