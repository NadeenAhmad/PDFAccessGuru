import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li import (
    correct_standard_type_remapped,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.utils import (
    generate_test_result_path,
    generate_resource_path,
)


def test_correct_standard_type_remapped():
    """
    Test for rule 7.1-7: a standard structure type is remapped inside /RoleMap.

    This verifies the corrector removes the illegal role mapping and rewrites the
    affected structure element to a valid standard type.
    """
    violation = Violation(
        category=ViolationCategory.SYNTAX,
        name="standard-type-remapped",
        description="",
        guidelines=[],
    )

    pdf_path = generate_resource_path("veraPDF_corpus/7.1-t07-fail-a.pdf")
    result_path = generate_test_result_path("7.1-t07-fail-a_corrected.pdf")

    with pikepdf.open(pdf_path) as pdf:
        affected_element = pdf.Root.get("/StructTreeRoot").get("/K")[0]
        detected_violation = DetectedViolation(
            violation=violation,
            affected_element=affected_element,
            supplementary_information=[],
        )

        correct_standard_type_remapped(detected_violation, pdf)
        pdf.save(result_path)

    verapdf_violations = run_verapdf(result_path)
    for v_violation in verapdf_violations:
        assert v_violation.rule_id != "7.1-7"
