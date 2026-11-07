import importlib
from typing import Callable, cast

from pikepdf import Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


# T02 and T03 are the two veraPDF reports for the same mixed heading style.
# Reusing one engine keeps context extraction and LLM validation consistent.
_NUMBERED_HEADING_CORRECTOR_MODULE = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax."
    "syntax_correctors_5_brian_karle.7_4_4_t02_document_uses_h_h_sharp_tags"
)
_correct_mixed_heading_tags = cast(
    Callable[[DetectedViolation, Pdf], None],
    getattr(
        _NUMBERED_HEADING_CORRECTOR_MODULE,
        "correct_document_uses_h_h_sharp_tags",
    ),
)


@corrector("document-uses-hn-h-tags")
def correct_document_uses_hn_h_tags(
    detected_violation: DetectedViolation,
    pdf: Pdf,
) -> None:
    """
    Correct veraPDF rule 7.4.4-3.

    veraPDF reports this rule on an existing numbered /H1 through /H6 when the
    same document also contains unnumbered /H tags. The shared correction engine
    finds every unnumbered heading, gives its full hierarchy and MCID text to the
    LLM, validates one /H1 through /H6 assignment per candidate, and then changes
    only those unnumbered tags. Existing numbered headings remain unchanged.
    """
    # Delegate to the general mixed-heading engine used by the equivalent T02 rule.
    _correct_mixed_heading_tags(detected_violation, pdf)
