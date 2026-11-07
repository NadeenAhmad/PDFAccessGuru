from pathlib import Path

import pikepdf
from pikepdf import Object

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
    correct_page_annotation_tabs_s,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.utils import (
    assert_verapdf_violation_removed,
    build_detected_syntax_violation,
    generate_resource_path,
    generate_test_output_path,
)


def test_correct_page_annotation_tabs_s(tmp_path: Path):
    """
    corrector test for rule 7.18.3-1.

    The affected element is the page dictionary itself. After correction,
    veraPDF should no longer report that this page is missing /Tabs /S.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.3-t01-fail-a.pdf")
    context_path = "root/document[0]/pages[0](82 0 obj PDPage)"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj  # type: ignore[assignment]
        detected_violation = build_detected_syntax_violation(
            "page-annotation-tabs-s",
            affected_element,
        )

        correct_page_annotation_tabs_s(detected_violation, pdf)

        result_path = generate_test_output_path("7.18.3-1-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.18.3-1", context_path)
