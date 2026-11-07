from pathlib import Path

import pikepdf
from pikepdf import Object

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
    correct_annotation_subtype_trapnet_exists,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.utils import (
    assert_verapdf_violation_removed,
    build_detected_syntax_violation,
    generate_resource_path,
    generate_test_output_path,
)


def test_correct_annotation_subtype_trapnet_exists(tmp_path: Path):
    """
    Template for corrector tests:
    1. open a failing PDF fixture
    2. resolve the affected element manually
    3. call the corrector
    4. save the corrected PDF to tmp_path
    5. assert veraPDF no longer reports the same violation on the same context
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.2-t01-fail-a.pdf")
    context_path = "root/document[0]/pages[0](35 0 obj PDPage)/annots[0](28 0 obj PDTrapNetAnnot)"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj.get("/Annots")[0]  # type: ignore[index]
        detected_violation = build_detected_syntax_violation(
            "annotation-subtype-trapnet-exists",
            affected_element,
        )

        correct_annotation_subtype_trapnet_exists(detected_violation, pdf)

        result_path = generate_test_output_path("7.18.2-1-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.18.2-1", context_path)
