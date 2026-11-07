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



def test_correct_link_annotation_missing_alternate_description_contents(tmp_path: Path):
    """
    corrector test for rule 7.18.5-2.

    The affected element is the link annotation dictionary in the page's
    /Annots array. The corrector uses the real OpenRouter provider(so this test can only pass if you have the api key saved in ur .env file, otherwise the test will be skipped) to generate
    the missing /Contents value.
    """
    load_environment_variables()
    if not os.environ.get("OPENROUTER_API_KEY"):
        pytest.skip("OPENROUTER_API_KEY is required to run this real OpenRouter provider test.")

    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
        link_annotation_missing_alternate_description_contents as link_contents_corrector,
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.18.5-t02-fail-a.pdf")
    context_path = "root/document[0]/pages[0](30 0 obj PDPage)/annots[0](23 0 obj PDLinkAnnot)"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj.get("/Annots")[0]  # type: ignore[index]
        detected_violation = build_detected_syntax_violation(
            "link-annotation-missing-alternate-description-contents",
            affected_element,
        )

        link_contents_corrector.correct_link_annotation_missing_alternate_description_contents(
            detected_violation,
            pdf,
        )

        assert str(affected_element.get("/Contents", "")).strip()

        result_path = generate_test_output_path("7.18.5-2-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.18.5-2", context_path)
