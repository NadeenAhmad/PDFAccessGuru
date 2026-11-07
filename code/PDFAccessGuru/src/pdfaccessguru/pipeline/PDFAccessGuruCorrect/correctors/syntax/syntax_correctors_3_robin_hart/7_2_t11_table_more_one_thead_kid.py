from pikepdf import Array, Name, Pdf
import pikepdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.exceptions.corrector_exceptions.could_not_extract_children_exception import CouldNotExtractChildrenException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart.utils import normalize_children_of_element


@corrector("table-more-one-thead-kid")
def correct_table_more_one_thead_kid(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-11
    Violation description: Table element contains more than one THead kid

    Correction strategy:
    A /Table may contain at most one /THead element.
    When multiple /THead kids are found, their /TR rows are merged into the
    first /THead and the duplicate /THead containers are removed.

    Before correction:

    ...|
       |_/Table|
               |_/THead|
                       |_/TR
               |_/THead|
                       |_/TR
               |_/TBody
               |...

    After correction:

    ...|
       |_/Table|
               |_/THead|
                       |_/TR
                       |_/TR
               |_/TBody
               |...

    """

    affected_element = detected_violation.affected_element

    if '/K' not in affected_element:
        raise CouldNotCorrectDetectedViolationException("table-more-one-thead-kid")
    try :
        child_elements = normalize_children_of_element(affected_element)
    except CouldNotExtractChildrenException as e :
        raise CouldNotCorrectDetectedViolationException("invalid-elements-li") from e

    primary_thead_element = None
    children_affected_element_corrected = Array()
    modified = False

    for child_element in child_elements:
        if isinstance(child_element, pikepdf.Dictionary) and child_element.get('/S') == Name('/THead'):

            if primary_thead_element is None:
                primary_thead_element = child_element
                children_affected_element_corrected.append(primary_thead_element)

                if '/K' not in primary_thead_element:
                    primary_thead_element['/K'] = Array()
                elif isinstance(primary_thead_element['/K'], pikepdf.Dictionary):
                    primary_thead_element['/K'] = Array([primary_thead_element['/K']])

            else:
                modified = True

                if '/K' in child_element:
                    children_duplicate_thead_element = child_element['/K']

                    if isinstance(children_duplicate_thead_element, pikepdf.Dictionary):
                        tr_elements_to_move = [children_duplicate_thead_element]
                    elif isinstance(children_duplicate_thead_element, pikepdf.Array):
                        tr_elements_to_move = list(children_duplicate_thead_element)
                    else:
                        tr_elements_to_move = []

                    for tr_element in tr_elements_to_move:
                        primary_thead_element['/K'].append(tr_element)

                        if isinstance(tr_element, pikepdf.Dictionary):
                            tr_element['/P'] = primary_thead_element

        else:
            children_affected_element_corrected.append(child_element)

    if modified:
        affected_element['/K'] = children_affected_element_corrected
