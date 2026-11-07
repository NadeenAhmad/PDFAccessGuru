import pikepdf
from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.artifacts import fix_tagged_artifacts
from pdfaccessguru.pipeline.reporting.writer import report_info


@corrector("tagged-content-inside-artifact")
def correct_tagged_content_inside_artifact(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.1-2
    Violation: content is marked as decoration (Artifact) and is also referenced by a tag.

    Fix (whole page at once, see structure_repair/artifacts.py): if the tag is named "Artifact",
    the content stays decoration and the empty tag is removed; for any other tag the content
    becomes real content of that tag. The first version turned such content into decoration in
    every case, hiding text from screen readers. Tagged content nested deeper inside decoration
    is left for re-tagging (Phase 6).
    """
    affected = detected_violation.affected_element
    page_obj = affected.obj if isinstance(affected, pikepdf.Page) else affected
    page = next((p for p in pdf.pages if isinstance(page_obj, pikepdf.Dictionary)
                 and page_obj.is_indirect and p.obj.objgen == page_obj.objgen), None)
    if page is None:
        raise CouldNotCorrectDetectedViolationException("tagged-content-inside-artifact: the page was not found")
    result = fix_tagged_artifacts(pdf, page)
    if result.made_content:
        report_info(f"{result.made_content} piece(s) of text marked as decoration but also tagged are now real content.")
    if result.kept_decoration:
        report_info(f"{result.kept_decoration} piece(s) of decoration had a tag named Artifact; the tag was removed.")
    if result.nested and not (result.made_content or result.kept_decoration):
        raise CouldNotCorrectDetectedViolationException(
            "tagged text inside a block marked as decoration: the page needs to be tagged again")
