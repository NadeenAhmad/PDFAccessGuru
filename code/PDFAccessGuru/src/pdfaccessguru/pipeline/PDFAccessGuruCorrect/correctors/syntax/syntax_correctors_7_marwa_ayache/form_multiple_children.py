from .common import CouldNotCorrectDetectedViolationException, DetectedViolation, Name, Pdf, corrector, pikepdf


@corrector("form-multiple-children")
def correct_form_multiple_children(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.18.4-2

    Violation description:
    The /Form structure element does not have exactly one child identifying the
    widget annotation.

    Correction strategy:
    The detected affected element is the /Form structure element itself. For the
    deterministic corpus case, its /K entry contains one valid /OBJR child that
    points to the widget annotation plus additional invalid children. Keep the
    single /OBJR child and remove all others so the /Form element has exactly
    one child identifying the widget annotation.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("form-multiple-children")

    if affected_element.get("/S") != Name("/Form"):
        raise CouldNotCorrectDetectedViolationException("form-multiple-children")

    kids = affected_element.get("/K")

    if isinstance(kids, pikepdf.Dictionary):
        if kids.get("/Type") == Name("/OBJR"):
            return
        raise CouldNotCorrectDetectedViolationException("form-multiple-children")

    if not isinstance(kids, pikepdf.Array):
        raise CouldNotCorrectDetectedViolationException("form-multiple-children")

    objr_children = [
        child for child in kids
        if isinstance(child, pikepdf.Dictionary) and child.get("/Type") == Name("/OBJR")
    ]

    if len(objr_children) != 1:
        raise CouldNotCorrectDetectedViolationException("form-multiple-children")

    affected_element["/K"] = objr_children[0]
