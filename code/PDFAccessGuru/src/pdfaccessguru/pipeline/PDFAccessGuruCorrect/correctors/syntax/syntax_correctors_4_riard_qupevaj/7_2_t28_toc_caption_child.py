import pikepdf
from pikepdf import Array, Name, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.exceptions.corrector_exceptions.could_not_extract_children_exception import (
    CouldNotExtractChildrenException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.utils import (
    normalize_children_of_element,
)


@corrector("toc-caption-child")
def correct_toc_caption_child(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-28
    Move /Caption children to the beginning of the /TOC children array.
    """
    affected_element = detected_violation.affected_element
    if not isinstance(affected_element, pikepdf.Dictionary) or affected_element.get("/S") != Name("/TOC"):
        raise CouldNotCorrectDetectedViolationException("toc-caption-child")

    try:
        children = normalize_children_of_element(affected_element)
    except CouldNotExtractChildrenException as error:
        raise CouldNotCorrectDetectedViolationException("toc-caption-child") from error

    captions = [
        child for child in children
        if isinstance(child, pikepdf.Dictionary) and child.get("/S") == Name("/Caption")
    ]
    if not captions:
        return

    others = [child for child in children if child not in captions]
    if children == captions + others:
        return

    affected_element["/K"] = Array(captions + others)
