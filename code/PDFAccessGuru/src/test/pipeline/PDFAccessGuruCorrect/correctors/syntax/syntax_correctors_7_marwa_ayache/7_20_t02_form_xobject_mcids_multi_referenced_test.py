from pathlib import Path

import pikepdf
from pikepdf import Object

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
    correct_form_xobject_mcids_multi_referenced,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.utils import (
    assert_verapdf_violation_removed,
    build_detected_syntax_violation,
    generate_resource_path,
    generate_test_output_path,
)


#this tests resolves 2 violations simultaneously
def test_correct_form_xobject_mcids_multi_referenced(tmp_path: Path):
    """
    corrector test for rule 7.20-2.

    The affected element is the Form XObject dictionary under
    /Resources -> /XObject -> /Fm0.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.20-t02-fail-a.pdf")
    context_path = "root/document[0]/pages[0](11 0 obj PDPage)/contentStream[0](18 0 obj PDSemanticContentStream)/operators[23]/xObject[0]"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj.get("/Resources").get("/XObject").get("/Fm0")  # type: ignore[assignment]
        detected_violation = build_detected_syntax_violation(
            "form-xobject-mcids-multi-referenced",
            affected_element,
        )

        correct_form_xobject_mcids_multi_referenced(detected_violation, pdf)

        result_path = generate_test_output_path("7.20-2-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.20-2", context_path)
