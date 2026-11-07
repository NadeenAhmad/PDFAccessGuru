from pikepdf import Pdf
import pikepdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import normalize_kids


@corrector("parent-entry-missing")
def correct_parent_entry_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.1-12

    Violation: A structure element is missing the /P (parent) entry.

    Fix: Search the structure tree for the element that contains the affected
    element as a child, and set its reference as /P.

    NOTE: No test PDF available in corpus. Implementation based on rule definition only.
    """
    def find_parent(node: pikepdf.Object, target: pikepdf.Object) -> pikepdf.Object | None:
        kids = normalize_kids(node)
        for kid in kids:
            if not isinstance(kid, pikepdf.Dictionary):
                continue
            if kid == target:
                return node
            result = find_parent(kid, target)
            if result is not None:
                return result
        return None

    affected_element = detected_violation.affected_element
    struct_tree_root = pdf.Root.get('/StructTreeRoot')
    if struct_tree_root is None:
        raise CouldNotCorrectDetectedViolationException("parent-entry-missing")

    parent = find_parent(struct_tree_root, affected_element)
    if parent is None:
        raise CouldNotCorrectDetectedViolationException("parent-entry-missing")

    affected_element['/P'] = parent
