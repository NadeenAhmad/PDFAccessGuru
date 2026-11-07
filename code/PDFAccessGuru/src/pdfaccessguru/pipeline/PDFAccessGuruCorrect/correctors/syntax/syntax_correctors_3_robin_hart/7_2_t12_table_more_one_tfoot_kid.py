from pikepdf import Array, Name, Pdf
import pikepdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.exceptions.corrector_exceptions.could_not_extract_children_exception import CouldNotExtractChildrenException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart.utils import normalize_children_of_element


@corrector("table-more-one-tfoot-kid")
def correct_table_more_one_tfoot_kid(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-12
    Violation description: Table element contains more than one TFoot kid

    Correction strategy:
    A /Table may contain at most one /TFoot element.
    When multiple /TFoot kids are found, their /TR rows are merged into the
    first /TFoot and the duplicate /TFoot containers are removed.

    Before correction:

    ...|
       |_/Table|
               |_/TBody
               |_/TFoot|
                        |_/TR
               |_/TFoot|
                        |_/TR
               |...

    After correction:

    ...|
       |_/Table|
               |_/TBody
               |_/TFoot|
                        |_/TR
                        |_/TR
               |...

    """

    affected_element = detected_violation.affected_element

    if '/K' not in affected_element:
        raise CouldNotCorrectDetectedViolationException("table-more-one-tfoot-kid")
    try :
        child_elements = normalize_children_of_element(affected_element)
    except CouldNotExtractChildrenException as e :
        raise CouldNotCorrectDetectedViolationException("invalid-elements-li") from e

    primary_tfoot_element = None
    children_affected_element_corrected = Array()
    modified = False

    for child_element in child_elements:
        if isinstance(child_element, pikepdf.Dictionary) and child_element.get('/S') == Name('/TFoot'):

            if primary_tfoot_element is None:
                primary_tfoot_element = child_element
                children_affected_element_corrected.append(primary_tfoot_element)

                if '/K' not in primary_tfoot_element:
                    primary_tfoot_element['/K'] = Array()
                elif isinstance(primary_tfoot_element['/K'], pikepdf.Dictionary):
                    primary_tfoot_element['/K'] = Array([primary_tfoot_element['/K']])

            else:
                modified = True

                if '/K' in child_element:
                    children_duplicate_tfoot_element = child_element['/K']

                    if isinstance(children_duplicate_tfoot_element, pikepdf.Dictionary):
                        tr_elements_to_move = [children_duplicate_tfoot_element]
                    elif isinstance(children_duplicate_tfoot_element, pikepdf.Array):
                        tr_elements_to_move = list(children_duplicate_tfoot_element)
                    else:
                        tr_elements_to_move = []

                    for tr_element in tr_elements_to_move:
                        primary_tfoot_element['/K'].append(tr_element)

                        if isinstance(tr_element, pikepdf.Dictionary):
                            tr_element['/P'] = primary_tfoot_element

        else:
            children_affected_element_corrected.append(child_element)

    if modified:
        affected_element['/K'] = children_affected_element_corrected
