from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.lists import ListRepair
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tree import Roles


@corrector("li-not-contained-l")
def correct_li_not_contained_l(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-17
    Violation: a list item (LI) is not inside a list (L).

    Fix (see structure_repair/lists.py): consecutive loose items become ONE list; items right
    after a list join that list (e.g. a list split by a page break). The earlier version
    created a separate one-item list for every item.

    The affected element is the parent of the loose item (or the item itself).
    """
    element = detected_violation.affected_element
    if not isinstance(element, Dictionary):
        raise CouldNotCorrectDetectedViolationException("li-not-contained-l: the affected element is not a structure element")
    parent = element.get("/P") if Roles(pdf).is_(element, "LI") else element
    if not isinstance(parent, Dictionary):
        raise CouldNotCorrectDetectedViolationException("li-not-contained-l: the list item has no parent")
    repair = ListRepair(pdf)
    if not repair.repair_parent(parent):
        # the reported location can point at the wrong element: search the whole document
        repair.repair_all_loose_items()
