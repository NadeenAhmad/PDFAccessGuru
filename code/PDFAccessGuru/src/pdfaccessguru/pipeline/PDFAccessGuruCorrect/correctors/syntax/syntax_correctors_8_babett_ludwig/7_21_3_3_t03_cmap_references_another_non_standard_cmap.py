import pikepdf
from pikepdf import Pdf
from pdfaccessguru.model.detected_violation import DetectedViolation

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


@corrector("cmap-references-another-non-standard-cmap")
def correct_cmap_references_another_non_standard_cmap(
    detected_violation: DetectedViolation,
    pdf: Pdf,
):
    """
    Corrects a Type0 font whose Encoding references a non-standard CMap.

    The function first retrieves the font affected by the detected
    violation and checks whether it contains an /Encoding entry. Only
    named encodings are handled, so the function returns if the Encoding
    is not a pikepdf.Name.

    The name of the referenced CMap is then compared against a list of
    supported standard CMaps. If the font already uses one of these
    standard CMaps, no correction is necessary.

    For a Type0 font that references a non-standard CMap, the function
    replaces the /Encoding entry with /Identity-H. This provides the
    standard Encoding used by the corrector to resolve the detected
    violation.

    The correction is intentionally limited to Type0 fonts. If the font
    is not a Type0 font, the function does not make any changes.
    """

    font = detected_violation.affected_element

    if "/Encoding" not in font:
        return

    encoding = font["/Encoding"]

    # Only named encodings can be handled by this corrector.
    if not isinstance(encoding, pikepdf.Name):
        return

    cmap_name = str(encoding)

    allowed = {
        "/Identity-H",
        "/Identity-V",
        "/UniJIS-UCS2-H",
        "/UniKS-UCS2-H",
        "/UniGB-UCS2-H",
    }

    if cmap_name in allowed:
        return

    # Standard solution for Type0 fonts.
    if font.get("/Subtype") == "/Type0":
        font["/Encoding"] = pikepdf.Name("/Identity-H")
