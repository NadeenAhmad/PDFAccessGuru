from pikepdf import Array, Dictionary, Name, Pdf
import pikepdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import normalize_kids


@corrector("tr-element-missing")
def correct_tr_element_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-4
    """
    """
    VeraPdf rule_id: 7.2-4
    Violation: TR element is not contained in Table, THead, TBody or TFoot.

    Fix: Find the nearest Table element in the structure tree and move the TR
    into a TBody under that Table. If no TBody exists, create one.

    Before:
        /Document
            |_/TR   <- wrong position

    After:
        /Document
            |_/Table
                |_/TBody
                    |_/TR
    """
    tr_element = detected_violation.affected_element
    parent = tr_element.get('/P')

    if parent is None:
        raise CouldNotCorrectDetectedViolationException("tr-element-missing")

    # Find nearest Table in siblings or parent
    def find_table(node: pikepdf.Object) -> pikepdf.Object | None:
        kids = normalize_kids(node)
        for kid in kids:
            if isinstance(kid, pikepdf.Dictionary) and kid.get('/S') == Name('/Table'):
                return kid
        return None

    table = find_table(parent)
    if table is None:
        raise CouldNotCorrectDetectedViolationException("tr-element-missing")

    # Remove TR from current parent
    if '/K' in parent:
        p_kids = parent['/K']
        if isinstance(p_kids, pikepdf.Array):
            parent['/K'] = Array([k for k in p_kids if k != tr_element])
        elif p_kids == tr_element:
            del parent['/K']

    # Find or create TBody under Table
    table_kids = normalize_kids(table)
    tbody = next((k for k in table_kids
                  if isinstance(k, pikepdf.Dictionary) and k.get('/S') == Name('/TBody')), None)

    if tbody is None:
        tbody = pdf.make_indirect(Dictionary({
            '/Type': Name('/StructElem'),
            '/S': Name('/TBody'),
            '/P': table,
            '/K': Array()
        }))
        table_kids.append(tbody)
        table['/K'] = Array(table_kids)

    # Add TR to TBody
    tbody_kids = normalize_kids(tbody)
    tbody_kids.append(tr_element)
    tbody['/K'] = Array(tbody_kids)
    tr_element['/P'] = tbody
