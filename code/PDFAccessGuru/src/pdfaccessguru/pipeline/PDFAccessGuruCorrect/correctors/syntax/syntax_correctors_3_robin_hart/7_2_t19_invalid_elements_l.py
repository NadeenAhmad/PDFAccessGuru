from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.lists import ListRepair
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles


@corrector("invalid-elements-l")
def correct_invalid_elements_l(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-19
    Violation: a list (L) contains something other than list items, lists or a caption.

    Fix (see structure_repair/lists.py): a loose label and the body after it become ONE item;
    a short text or Span right before an item without a label (e.g. the bullet) becomes that
    item's label; text that continues the item before it joins that item; anything else
    becomes an item of its own. The earlier version split labels and text into separate items.
    """
    element = detected_violation.affected_element
    if not isinstance(element, Dictionary) or not Roles(pdf).is_(element, "L"):
        raise CouldNotCorrectDetectedViolationException("invalid-elements-l: the affected element is not a L")
    ListRepair(pdf).repair_list(element)
