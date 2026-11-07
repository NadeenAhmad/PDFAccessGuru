from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.programs import set_identity_cid_to_gid

from .common import CouldNotCorrectDetectedViolationException, DetectedViolation, Pdf, corrector


@corrector("invalid-type-2-cidfont")
def correct_invalid_type_2_cidfont(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.21.3.2-1

    Violation description:
    An embedded Type 2 CIDFont has a missing or invalid /CIDToGIDMap entry.

    Correction strategy (all fonts at once, see font_repair/programs.py):
    A missing or invalid map is set to /Identity, which is what viewers already use when the
    entry is missing (ISO 32000-1, Table 117), so the page does not change. An existing map
    stream is never replaced (the first version overwrote it, which can garble subset fonts).
    """
    result = set_identity_cid_to_gid(pdf)
    if not result.fixed:
        raise CouldNotCorrectDetectedViolationException("invalid-type-2-cidfont: no font with a missing or invalid map found")
