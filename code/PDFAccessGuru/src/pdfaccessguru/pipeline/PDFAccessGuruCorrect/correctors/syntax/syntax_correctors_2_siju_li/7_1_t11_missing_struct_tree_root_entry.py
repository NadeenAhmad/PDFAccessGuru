from pikepdf import Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_info, report_review
from pdfaccessguru.tagging.builder import tag_document


@corrector("missing-struct-tree-root-entry")
def correct_missing_struct_tree_root_entry(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.1-11
    Violation: the document has no tags (no structure tree).

    Fix (Phase 6, see pdfaccessguru/tagging): the pages are read like a person reads them
    (headings and their levels, paragraphs, lists, pictures, captions, reading order also with two
    columns; headers, footers and page numbers become decoration), every piece of content is
    marked, and the tag tree is built. The pipeline checks that every page looks the same and the
    text is unchanged, otherwise the tagging is undone. The first version created an empty tree.
    """
    result = tag_document(pdf)
    if result.pages:
        parts = ", ".join(f"{count} {name}" for name, count in sorted(result.elements.items()))
        report_info(f"The file had no tags. Tags were added automatically on {result.pages} page(s): {parts}.")
        report_review("Tags were added automatically. Please check the reading order and the headings "
                      "once, for example with the tags panel of your PDF program or with a screen reader.")
