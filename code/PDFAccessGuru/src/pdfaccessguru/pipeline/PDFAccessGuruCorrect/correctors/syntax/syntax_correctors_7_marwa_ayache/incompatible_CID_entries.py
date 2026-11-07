from .common import CouldNotCorrectDetectedViolationException, DetectedViolation, Pdf, corrector, pikepdf


@corrector("incompatible-CID-entries")
def correct_incompatible_CID_entries(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.21.3.1-1

    Violation description:
    The CIDSystemInfo entries of the Type 0 font's descendant CIDFont and CMap
    are not compatible.

    Correction strategy:
    The affected element is the parent Type 0 font dictionary. In the corpus
    fail/pass pairs, the mismatch is in the descendant CIDFont's
    /CIDSystemInfo /Registry, /Ordering, and /Supplement values. To fix this, we deterministically sync the descendant
    CIDSystemInfo entries to the CMap's CIDSystemInfo entries.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("incompatible-CID-entries")

    descendant_fonts = affected_element.get("/DescendantFonts")
    encoding = affected_element.get("/Encoding")

    if not isinstance(descendant_fonts, pikepdf.Array) or len(descendant_fonts) == 0:
        raise CouldNotCorrectDetectedViolationException("incompatible-CID-entries")

    descendant_font = descendant_fonts[0]
    if not isinstance(descendant_font, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("incompatible-CID-entries")

    descendant_cidsysteminfo = descendant_font.get("/CIDSystemInfo")
    encoding_cidsysteminfo = encoding.get("/CIDSystemInfo") if hasattr(encoding, "get") else None # type: ignore

    if not isinstance(descendant_cidsysteminfo, pikepdf.Dictionary) or \
            not isinstance(encoding_cidsysteminfo, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("incompatible-CID-entries")

    for key in ["/Registry", "/Ordering", "/Supplement"]:
        if key in encoding_cidsysteminfo:
            descendant_cidsysteminfo[key] = encoding_cidsysteminfo.get(key)
