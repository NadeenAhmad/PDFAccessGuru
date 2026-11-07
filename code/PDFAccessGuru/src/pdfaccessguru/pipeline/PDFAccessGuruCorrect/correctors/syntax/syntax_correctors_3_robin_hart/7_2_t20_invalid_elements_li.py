from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.lists import ListRepair
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles


@corrector("invalid-elements-li")
def correct_invalid_elements_li(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-20
    Violation: a list item (LI) contains something other than a label (Lbl) and a body (LBody).

    Fix (see structure_repair/lists.py): the item keeps one label and one body; all other
    content (e.g. a figure next to the text, or a second body) joins the body in reading order.
    Marked content that moves is re-registered, so screen readers still find its owner.
    """
    element = detected_violation.affected_element
    if not isinstance(element, Dictionary) or not Roles(pdf).is_(element, "LI"):
        raise CouldNotCorrectDetectedViolationException("invalid-elements-li: the affected element is not a LI")
    ListRepair(pdf).repair_item(element)
