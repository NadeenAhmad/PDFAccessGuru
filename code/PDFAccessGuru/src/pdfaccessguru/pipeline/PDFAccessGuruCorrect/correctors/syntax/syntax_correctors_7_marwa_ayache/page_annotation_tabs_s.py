from .common import CouldNotCorrectDetectedViolationException, DetectedViolation, Name, Pdf, corrector, pikepdf


@corrector("page-annotation-tabs-s")
def correct_page_annotation_tabs_s(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.18.3-1

    Violation description:
    A page with annotation(s) does not contain a /Tabs key or its value is not /S.

    Correction strategy:
    The detected affected element is the page dictionary itself. This violation
    can be corrected deterministically by setting the page dictionary entry
    /Tabs to /S.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("page-annotation-tabs-s")

    affected_element["/Tabs"] = Name("/S")
