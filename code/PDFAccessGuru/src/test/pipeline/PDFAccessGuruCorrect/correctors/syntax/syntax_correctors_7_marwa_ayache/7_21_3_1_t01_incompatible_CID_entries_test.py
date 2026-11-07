from pathlib import Path

import pikepdf
from pikepdf import Object

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
    correct_incompatible_CID_entries,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.utils import (
    assert_verapdf_violation_removed,
    build_detected_syntax_violation,
    generate_resource_path,
    generate_test_output_path,
)


def test_correct_incompatible_CID_entries(tmp_path: Path):
    """
    corrector test for rule 7.21.3.1-1.

    The affected element is the parent Type 0 font dictionary under
    /Resources -> /Font -> /C0_0.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.21.3.1-t01-fail-a.pdf")
    context_path = "root/document[0]/pages[0](12 0 obj PDPage)/contentStream[0](21 0 obj PDSemanticContentStream)/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj.get("/Resources").get("/Font").get("/C0_0")  # type: ignore[assignment]
        detected_violation = build_detected_syntax_violation(
            "incompatible-CID-entries",
            affected_element,
        )

        correct_incompatible_CID_entries(detected_violation, pdf)

        result_path = generate_test_output_path("7.21.3.1-1-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.21.3.1-1", context_path)
