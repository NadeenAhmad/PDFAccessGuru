import os
import pikepdf


from pdfaccessguru.utils.environment_variables import load_environment_variables
from test.validation_set.utils import (
    correct_validation_violations,
    detect_validation_violations,
    validation_pdf_path,
    verapdf_rule_count,
)

def run_pdf_correction_test(
    pdf_path,
    rule_id,
    violation_name,
    expected_count,
    output_filename,
):
    load_environment_variables()

    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError(
            "OPENROUTER_API_KEY is required"
        )

    assert verapdf_rule_count(
        pdf_path,
        rule_id
    ) == expected_count


    with pikepdf.open(pdf_path) as pdf:

        detected_violations = detect_validation_violations(
            pdf_path,
            pdf,
            violation_name,
        )

        assert len(detected_violations) == expected_count


        result_path = correct_validation_violations(
            pdf,
            detected_violations,
            output_filename,
            violation_name,
        )


    assert result_path.exists()

    assert verapdf_rule_count(
        result_path,
        rule_id
    ) == 0