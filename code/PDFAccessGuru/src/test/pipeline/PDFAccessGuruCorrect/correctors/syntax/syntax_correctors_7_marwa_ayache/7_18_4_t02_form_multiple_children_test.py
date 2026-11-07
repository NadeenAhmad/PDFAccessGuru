from pathlib import Path

import pikepdf
from pikepdf import Object

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
    correct_form_multiple_children,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.utils import (
    assert_verapdf_violation_removed,
    build_detected_syntax_violation,
    generate_resource_path,
    generate_test_output_path,
)


def test_correct_form_multiple_children(tmp_path: Path):
    """
    corrector test for rule 7.18.4-2.

    The affected element is the /Form structure element in the logical
    structure tree. After correction, veraPDF should no longer report that this
    /Form element has multiple children instead of exactly one widget-identifying child.
    """
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.18.4-t02-fail-a.pdf")
    context_path = "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)/K[0](8 0 obj SEDocument Document)/K[3](10 0 obj SEForm Form)"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.Root.get("/StructTreeRoot").get("/K").get("/K")[3]  # type: ignore[assignment,index]
        detected_violation = build_detected_syntax_violation(
            "form-multiple-children",
            affected_element,
        )

        correct_form_multiple_children(detected_violation, pdf)

        result_path = generate_test_output_path("7.18.4-2-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.18.4-2", context_path)
