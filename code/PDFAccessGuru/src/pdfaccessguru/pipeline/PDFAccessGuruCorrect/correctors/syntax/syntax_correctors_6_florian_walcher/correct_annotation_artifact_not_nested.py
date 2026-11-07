from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.annotation_tags import tag_annotations
from pdfaccessguru.pipeline.reporting.writer import report_info


@corrector("annotation-artifact-not-nested")
def correct_annotation_artifact_not_nested(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.18.1-1
    Violation: an annotation (other than a form field, link or printer's mark) is not nested in
    an Annot tag.

    Fix (all annotations at once, see structure_repair/annotation_tags.py): each gets an Annot tag
    right after the tag of the text it covers (else after the last content of its page), and the
    parent tree is updated. The first version retagged the surrounding element and wrote a
    description taken from page 1.
    """
    if not hasattr(pdf.Root, "get") or pdf.Root.get("/StructTreeRoot") is None:
        raise CouldNotCorrectDetectedViolationException("the document has no tags yet (tagging comes in Phase 6)")
    result = tag_annotations(pdf)
    if result.tagged:
        report_info(f"{result.tagged} comment(s) or other annotation(s) were added to the tags, "
                    f"{result.placed_by_text} of them next to the text they mark.")
