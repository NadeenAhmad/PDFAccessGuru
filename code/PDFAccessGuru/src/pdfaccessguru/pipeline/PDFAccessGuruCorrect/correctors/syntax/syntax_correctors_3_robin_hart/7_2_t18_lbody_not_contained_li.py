from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.lists import ListRepair
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles


@corrector("lbody-not-contained-li")
def correct_lbody_not_contained_li(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-18
    Violation: a list body (LBody) is not inside a list item (LI).

    Fix (see structure_repair/lists.py): the body joins the item it belongs to: the item right
    before it that has no body yet (also the last item of the list right before it), or it
    forms a new item together with the label right before it. The earlier version separated
    labels from their text.

    The affected element is the parent of the loose body (or the body itself).
    """
    element = detected_violation.affected_element
    if not isinstance(element, Dictionary):
        raise CouldNotCorrectDetectedViolationException("lbody-not-contained-li: the affected element is not a structure element")
    parent = element.get("/P") if Roles(pdf).is_(element, "LBody") else element
    if not isinstance(parent, Dictionary):
        raise CouldNotCorrectDetectedViolationException("lbody-not-contained-li: the list body has no parent")
    repair = ListRepair(pdf)
    if not repair.repair_parent(parent):
        # the reported location can point at the wrong element: search the whole document
        repair.repair_all_loose_items()
