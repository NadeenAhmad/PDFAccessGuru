from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.roles import map_custom_types, report_role_map


@corrector("circular-mapping-exists")
def correct_circular_mapping_exists(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.1-6
    Violation: the role map contains a circle (A -> B -> A) that never reaches a standard tag.

    Fix (see structure_repair/roles.py): every name in the circle is mapped by what it says, or
    by what its tags contain. The first version mapped them all to a paragraph.
    """
    result = map_custom_types(pdf)
    report_role_map(result)
