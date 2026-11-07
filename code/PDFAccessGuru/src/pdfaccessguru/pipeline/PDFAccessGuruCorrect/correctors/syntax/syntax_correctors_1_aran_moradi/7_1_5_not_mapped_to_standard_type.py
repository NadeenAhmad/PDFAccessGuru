from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.roles import map_custom_types, report_role_map


@corrector("not-mapped-to-standard-type")
def correct_not_mapped_to_standard_type(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.1-5
    Violation: a custom tag name does not lead to a standard tag through the role map.

    Fix (all custom names of the document at once, see structure_repair/roles.py): each name is
    mapped by what it says ("Footnote" -> Note, "Überschrift 2" -> H2, "GoTo" -> Link,
    "Lbody" -> LBody); a name that says nothing is mapped by what its tags contain (a group or
    a paragraph) and listed for checking. The first version mapped every name to a paragraph.
    """
    result = map_custom_types(pdf)
    report_role_map(result)
