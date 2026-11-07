import os
from pathlib import Path

import pikepdf
import pytest
from pikepdf import Object

from pdfaccessguru.utils.environment_variables import load_environment_variables
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.utils import (
    assert_verapdf_violation_removed,
    build_detected_syntax_violation,
    generate_resource_path,
    generate_test_output_path,
)


def test_correct_alt_missing_media_clip_data(tmp_path: Path):
    """
    corrector test for rule 7.18.6.2-2.

    The affected element is the media clip data dictionary nested under the
    screen annotation action and rendition dictionaries. The corrector uses the
    real OpenRouter provider(so this test can only pass if you have the api key
    saved in ur .env file, otherwise the test will be skipped) to generate the
    missing /Alt value.
    """
    load_environment_variables()
    if not os.environ.get("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY is required to run this real OpenRouter provider test.")

    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
        alt_missing_media_clip_data as media_clip_corrector,
    )
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.alt_missing_media_clip_data import (
        extract_media_clip_data_bytes,
        get_media_clip_content_type,
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.18.6.2-t02-fail-a.pdf")
    context_path = "root/document[0]/pages[0](3 0 obj PDPage)/annots[0](8 0 obj PDScreenAnnot)/A[0]/C[0]"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj.get("/Annots")[0].get("/A").get("/R").get("/C")  # type: ignore[assignment]
        media_bytes = extract_media_clip_data_bytes(affected_element)  # type: ignore[arg-type]

        assert get_media_clip_content_type(affected_element) == "video/mp4"  # type: ignore[arg-type]
        assert media_bytes is not None
        assert media_bytes.startswith(b"\x1aE\xdf\xa3")

        detected_violation = build_detected_syntax_violation(
            "alt-missing-media-clip-data",
            affected_element,
        )

        media_clip_corrector.correct_alt_missing_media_clip_data(detected_violation, pdf)

        alt_value = affected_element.get("/Alt")
        assert alt_value is not None
        assert len(alt_value) == 4
        assert alt_value[0] == "en-US"
        assert str(alt_value[1]).strip()
        assert alt_value[2] == ""
        assert str(alt_value[3]).strip()

        result_path = generate_test_output_path("7.18.6.2-2-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.18.6.2-2", context_path)


def test_image_media_bytes_to_png_keeps_png_bytes():
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.alt_missing_media_clip_data import (
        image_media_bytes_to_png,
    )

    png_bytes = b"\x89PNG\r\n\x1a\nfake-png-data"

    assert image_media_bytes_to_png(png_bytes) == png_bytes


def test_image_media_bytes_to_png_returns_none_for_non_image_bytes():
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.alt_missing_media_clip_data import (
        image_media_bytes_to_png,
    )

    assert image_media_bytes_to_png(b"not image data") is None


def test_get_alt_language_uses_language_context_supplementary_information():
    from pdfaccessguru.model.supplementary_information.supplementary_information import (
        LanguageContextSupplementaryInformation,
    )
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.alt_missing_media_clip_data import (
        get_alt_language,
    )

    detected_violation = build_detected_syntax_violation(
        "alt-missing-media-clip-data",
        pikepdf.Dictionary(),
        [LanguageContextSupplementaryInformation("de", "page")],
    )

    assert get_alt_language(detected_violation) == "de"


def test_get_alt_language_falls_back_to_en_us_without_language_context():
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.alt_missing_media_clip_data import (
        get_alt_language,
    )

    detected_violation = build_detected_syntax_violation(
        "alt-missing-media-clip-data",
        pikepdf.Dictionary(),
    )

    assert get_alt_language(detected_violation) == "en-US"


def test_correct_alt_missing_media_clip_data_uses_fallback_alt_text(monkeypatch):
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
        alt_missing_media_clip_data as media_clip_corrector,
    )

    def fail_prompt(media_clip_data, language_tag):
        raise RuntimeError("LLM unavailable")

    monkeypatch.setattr(media_clip_corrector, "prompt_media_clip_alt_text", fail_prompt)

    affected_element = pikepdf.Dictionary()
    detected_violation = build_detected_syntax_violation(
        "alt-missing-media-clip-data",
        affected_element,
    )

    media_clip_corrector.correct_alt_missing_media_clip_data(
        detected_violation,
        pikepdf.Pdf.new(),
    )

    alt_value = affected_element.get("/Alt")
    assert alt_value is not None
    assert alt_value[0] == "en-US"
    assert alt_value[1] == "Embedded media content."
    assert alt_value[2] == ""
    assert alt_value[3] == "Embedded media content."
