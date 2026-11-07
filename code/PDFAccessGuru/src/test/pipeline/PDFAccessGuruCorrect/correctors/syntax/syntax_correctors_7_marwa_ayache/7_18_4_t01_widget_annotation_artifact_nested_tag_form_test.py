from pathlib import Path

import pikepdf
from pikepdf import Object

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
    correct_widget_annotation_artifact_nested_tag_form,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collect_supplementary_information import (
    collect_supplementary_information,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.utils import (
    assert_verapdf_violation_removed,
    build_detected_syntax_violation,
    build_verapdf_violation,
    generate_resource_path,
    generate_test_output_path,
)


def test_correct_widget_annotation_artifact_nested_tag_form(tmp_path: Path):
    """
    corrector test for rule 7.18.4-1.

    The affected element is the widget annotation dictionary in the page's
    /Annots array. After correction, veraPDF should no longer report that the
    widget annotation is not nested within a /Form tag.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.4-t01-fail-a.pdf")
    context_path = "root/document[0]/pages[0](51 0 obj PDPage)/annots[0](34 0 obj PDWidgetAnnot)"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj.get("/Annots")[0]  # type: ignore[index]
        supplementary_information = collect_supplementary_information(
            build_verapdf_violation("7.18.4-1", context_path),
            pdf,
            affected_element,
        )
        detected_violation = build_detected_syntax_violation(
            "widget-annotation-artifact-nested-tag-form",
            affected_element,
            supplementary_information,
        )

        correct_widget_annotation_artifact_nested_tag_form(detected_violation, pdf)

        result_path = generate_test_output_path("7.18.4-1-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.18.4-1", context_path)
