from .common import CouldNotCorrectDetectedViolationException, DetectedViolation, Pdf, corrector, pikepdf


@corrector("annotation-subtype-trapnet-exists")
def correct_annotation_subtype_trapnet_exists(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.18.2-1

    Violation description:
    An annotation of subtype /TrapNet exists.

    Correction strategy:
    TrapNet annotations are not allowed for this rule. The affected element
    returned by detection is the annotation dictionary itself, so the
    deterministic repair is to remove that annotation from the page's /Annots
    array.
    """
    affected_element = detected_violation.affected_element

    for page in pdf.pages:
        page_dict = page.obj
        annots = page_dict.get("/Annots")

        if not isinstance(annots, pikepdf.Array):
            continue

        for index, annot in enumerate(annots):
            if annot != affected_element:
                continue

            del annots[index]

            if len(annots) == 0:
                del page_dict["/Annots"]

            return

    raise CouldNotCorrectDetectedViolationException("annotation-subtype-trapnet-exists")
