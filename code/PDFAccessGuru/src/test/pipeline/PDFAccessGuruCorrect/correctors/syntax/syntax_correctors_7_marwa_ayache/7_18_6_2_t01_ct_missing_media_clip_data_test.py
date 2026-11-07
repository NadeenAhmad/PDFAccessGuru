from pathlib import Path

import pikepdf
from pikepdf import Object

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
    correct_ct_missing_media_clip_data,
)
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.ct_missing_media_clip_data import (
    infer_content_type_from_bytes,
    infer_media_clip_content_type,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.utils import (
    assert_verapdf_violation_removed,
    build_detected_syntax_violation,
    generate_resource_path,
    generate_test_output_path,
)


def test_correct_ct_missing_media_clip_data(tmp_path: Path):
    """
    corrector test for rule 7.18.6.2-1.

    The affected element is the media clip data dictionary nested under the
    screen annotation action and rendition dictionaries.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.6.2-t01-fail-a.pdf")
    context_path = "root/document[0]/pages[0](3 0 obj PDPage)/annots[0](8 0 obj PDScreenAnnot)/A[0]/C[0]"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj.get("/Annots")[0].get("/A").get("/R").get("/C")  # type: ignore[assignment]
        detected_violation = build_detected_syntax_violation(
            "ct-missing-media-clip-data",
            affected_element,
        )

        correct_ct_missing_media_clip_data(detected_violation, pdf)
        assert affected_element.get("/CT") == "video/webm"

        result_path = generate_test_output_path("7.18.6.2-1-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.18.6.2-1", context_path)


def test_infer_media_clip_content_type_falls_back_to_empty_string():
    media_clip_data = pikepdf.Dictionary()

    assert infer_content_type_from_bytes(b"unknown media bytes") is None
    assert infer_media_clip_content_type(media_clip_data) == ""
