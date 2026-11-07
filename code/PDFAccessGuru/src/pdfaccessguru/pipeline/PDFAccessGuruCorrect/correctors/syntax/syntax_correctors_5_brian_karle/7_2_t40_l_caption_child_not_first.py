from pikepdf import Array, Dictionary, Name, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector

def _is_name(value, expected: str) -> bool:
    return str(value) == expected


def _get_structure_type(element):
    return element.get("/S") if hasattr(element, "get") else None


@corrector("l-caption-child-not-first")
def correct_l_caption_child_not_first(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-40

    Violation description: L element contains Caption child not as its first one

    Correction strategy:
    The caption is in the wrong position and must only be moved to the correct position 
    by changing the order of the childs.
    """

    affected_element = detected_violation.affected_element

    if not _is_name(_get_structure_type(affected_element), "/L"):
        raise CouldNotCorrectDetectedViolationException(
            detected_violation.violation.name
        )

    children = affected_element.get("/K")
    if not isinstance(children, Array):
        raise CouldNotCorrectDetectedViolationException(
            detected_violation.violation.name
        )

    caption_index = None
    for index, child in enumerate(children):
        if _is_name(_get_structure_type(child), "/Caption"):
            caption_index = index
            break

    if caption_index is None:
        raise CouldNotCorrectDetectedViolationException(
            detected_violation.violation.name
        )

    if caption_index == 0:
        return

    corrected_children = Array()
    corrected_children.append(children[caption_index])

    for index, child in enumerate(children):
        if index != caption_index:
            corrected_children.append(child)

    affected_element["/K"] = corrected_children