from pikepdf import Dictionary, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.toc_and_headings import repair_headings


@corrector("node-more-one-h-tag")
def correct_node_more_one_h_tag(detected_violation: DetectedViolation, pdf: Pdf) -> None:
    """
    VeraPdf rule_id: 7.4.4-1
    Violation: a node contains more than one unnumbered heading (H). With H tags, the level of a
    heading comes from how deeply its section is nested, so each section may have one heading.

    Fix (see structure_repair/toc_and_headings.py): every heading keeps its tag and gets its own
    section, which starts at the heading and ends before the next one:

        Sect(H, P, H, P)   ->   Sect(H, P), Sect(H, P)                  (same level as before)
        Document(H, P, H)  ->   Document(Sect(H, P), Sect(H))           (all one level deeper)

    The earlier version asked an LLM which headings to turn into normal paragraphs.
    """
    node = detected_violation.affected_element
    if not isinstance(node, Dictionary) or "/S" not in node:
        raise CouldNotCorrectDetectedViolationException("node-more-one-h-tag: the affected element is not a structure element")
    repair_headings(pdf, node)
