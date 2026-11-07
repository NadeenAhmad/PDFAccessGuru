from pathlib import Path

import pikepdf
from pikepdf import Object

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
    correct_invalid_type_2_cidfont,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.utils import (
    assert_verapdf_violation_removed,
    build_detected_syntax_violation,
    generate_resource_path,
    generate_test_output_path,
)


def test_correct_invalid_type_2_cidfont(tmp_path: Path):
    """
    corrector test for rule 7.21.3.2-1.

    The affected element is the descendant CIDFont dictionary under
    /Resources -> /Font -> /C2_0 -> /DescendantFonts[0].
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.3.2-t01-fail-a.pdf")
    context_path = "root/document[0]/pages[0](3 0 obj PDPage)/contentStream[0](9 0 obj PDSemanticContentStream)/operators[9]/font[0](GITMIG+LiberationSans,Bold)/DescendantFonts[0](GITMIG+LiberationSans,Bold)"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj.get("/Resources").get("/Font").get("/C2_0").get("/DescendantFonts")[0]  # type: ignore[assignment]
        detected_violation = build_detected_syntax_violation(
            "invalid-type-2-cidfont",
            affected_element,
        )

        correct_invalid_type_2_cidfont(detected_violation, pdf)

        result_path = generate_test_output_path("7.21.3.2-1-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.21.3.2-1", context_path)
