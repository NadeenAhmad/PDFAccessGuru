from pikepdf import Array, Name, Pdf
import pikepdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.exceptions.corrector_exceptions.could_not_extract_children_exception import CouldNotExtractChildrenException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart.utils import normalize_children_of_element


@corrector("table-caption-child")
def correct_table_caption_child(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-16
    Violation description: Table element contains Caption not as its first or last child

    Correction strategy:
    A /Caption element must be the first direct child of a /Table element.
    When /Caption elements appear after other table children, they are moved
    to the front of the table's /K array.

    Before correction:

    ...|
       |_/Table|
               |_/THead
               |_/Caption
               |_/TBody
               |...

    After correction:

    ...|
       |_/Table|
               |_/Caption
               |_/THead
               |_/TBody
               |...

    """

    affected_element = detected_violation.affected_element

    if '/K' not in affected_element:
        raise CouldNotCorrectDetectedViolationException("table-caption-child")
    try :
        child_elements = normalize_children_of_element(affected_element)
    except CouldNotExtractChildrenException as e :
        raise CouldNotCorrectDetectedViolationException("invalid-elements-li") from e

    caption_elements = [
        child_element for child_element in child_elements
        if isinstance(child_element, pikepdf.Dictionary) and child_element.get('/S') == Name('/Caption')
    ]
    other_elements = [child_element for child_element in child_elements if child_element not in caption_elements]

    if caption_elements:
        children_affected_element_corrected = Array()
        for caption_element in caption_elements:
            children_affected_element_corrected.append(caption_element)
        for other_element in other_elements:
            children_affected_element_corrected.append(other_element)
        affected_element['/K'] = children_affected_element_corrected
