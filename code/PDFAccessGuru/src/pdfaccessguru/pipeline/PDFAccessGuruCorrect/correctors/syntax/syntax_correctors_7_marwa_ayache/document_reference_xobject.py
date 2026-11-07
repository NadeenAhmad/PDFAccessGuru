from .common import CouldNotCorrectDetectedViolationException, DetectedViolation, Pdf, corrector


@corrector("document-reference-xobject")
def correct_document_reference_xobject(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.20-1

    Violation description:
    The document contains a reference XObject via the /Ref key in a Form
    XObject dictionary.

    Correction strategy:
    The affected element is the Form XObject dictionary itself. In the corpus
    pass fixture, the repair is to remove the disallowed /Ref entry from that
    dictionary.
    """
    affected_element = detected_violation.affected_element

    if not hasattr(affected_element, "keys"):
        raise CouldNotCorrectDetectedViolationException("document-reference-xobject")

    if "/Ref" not in affected_element.keys():
        raise CouldNotCorrectDetectedViolationException("document-reference-xobject")

    del affected_element["/Ref"]
