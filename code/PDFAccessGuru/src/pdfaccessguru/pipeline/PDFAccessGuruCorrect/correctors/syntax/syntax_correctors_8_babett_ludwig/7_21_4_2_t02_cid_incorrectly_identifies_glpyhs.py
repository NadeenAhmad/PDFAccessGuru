from pikepdf import Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


@corrector("cid-incorrectly-identifies-glpyhs")
def correct_cid_incorrectly_identifies_glpyhs(
    detected_violation: DetectedViolation,
    pdf: Pdf,
):
    """Removes the invalid '/CIDSet' entry if present"""
    font_dict = detected_violation.affected_element

    if "/CIDSet" in font_dict:
        del font_dict["/CIDSet"]