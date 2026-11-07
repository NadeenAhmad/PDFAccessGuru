from pikepdf import Array, Dictionary, Name, Pdf
import pikepdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.exceptions.corrector_exceptions.could_not_extract_children_exception import CouldNotExtractChildrenException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart.utils import normalize_children_of_element


@corrector("table-thead-kid-not-tbody-kids")
def correct_table_thead_kid_not_tbody_kids(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-14
    Violation description: Table element contains THead kid, but does not contain TBody kids

    Correction strategy:
    A /Table that contains a /THead kid must also contain /TBody kids.
    When loose /TR rows exist directly under /Table without a /TBody container,
    they are wrapped inside a newly created /TBody element.

    Before correction:

    ...|
       |_/Table|
               |_/THead
               |_/TR
               |_/TR
               |...

    After correction:

    ...|
       |_/Table|
               |_/THead
               |_/TBody|
                        |_/TR
                        |_/TR
               |...

    """

    affected_element = detected_violation.affected_element

    if '/K' not in affected_element:
        raise CouldNotCorrectDetectedViolationException("table-thead-kid-not-tbody-kids")
    try :
        child_elements = normalize_children_of_element(affected_element)
    except CouldNotExtractChildrenException as e :
        raise CouldNotCorrectDetectedViolationException("invalid-elements-li") from e

    has_tbody_element = any(
        isinstance(child_element, pikepdf.Dictionary) and child_element.get('/S') == Name('/TBody')
        for child_element in child_elements
    )
    if has_tbody_element:
        raise CouldNotCorrectDetectedViolationException("table-thead-kid-not-tbody-kids")

    loose_tr_elements = [
        child_element for child_element in child_elements
        if isinstance(child_element, pikepdf.Dictionary) and child_element.get('/S') == Name('/TR')
    ]
    other_elements = [child_element for child_element in child_elements if child_element not in loose_tr_elements]

    if loose_tr_elements:
        new_tbody_element = pdf.make_indirect(Dictionary({
            '/Type': Name('/StructElem'),
            '/S': Name('/TBody'),
            '/P': affected_element
        }))

        children_new_tbody_element = Array()
        for tr_element in loose_tr_elements:
            children_new_tbody_element.append(tr_element)
            if isinstance(tr_element, pikepdf.Dictionary):
                tr_element['/P'] = new_tbody_element
        new_tbody_element['/K'] = children_new_tbody_element

        children_affected_element_corrected = Array()
        for other_element in other_elements:
            children_affected_element_corrected.append(other_element)
        children_affected_element_corrected.append(new_tbody_element)

        affected_element['/K'] = children_affected_element_corrected
