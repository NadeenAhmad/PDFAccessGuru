from pikepdf import Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.annotations import describe_annotations
from pdfaccessguru.pipeline.reporting.writer import report_info, report_review


@corrector("invalid-annotation")
def correct_invalid_annotation(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.18.1-2
    Violation: an annotation (other than a form field or a hidden one) has neither /Contents
    nor an /Alt on its tag.

    Fix (all annotations of the document at once, see correctors/descriptions/annotations.py):
    links get their visible text and target, highlights the marked text, comments their own
    text, attached files their file name, stamps their name; drawings and media get a short
    word and are listed for checking. No AI is needed. The first version retagged the
    surrounding structure element (e.g. a paragraph) as an annotation.
    """
    result = describe_annotations(pdf)
    if result.links or result.described:
        report_info(f"{result.links + result.described} annotation(s) got a description "
                    f"({result.links} link(s), {result.described} other).")
    if result.generic:
        report_review(f"{result.generic} annotation(s) (drawings, media or links without text) got only a short "
                      "general description. Please describe them better if they matter for the content.")
