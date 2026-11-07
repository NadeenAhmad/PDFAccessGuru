import pikepdf

from test.validation_set.utils import (
    correct_validation_violations,
    detect_validation_violations,
    validation_pdf_path,
    verapdf_rule_count,
)
from test.validation_set.generic_validation_Set_test import run_pdf_correction_test


PDF_FILENAME = "table_structure_FAILED_W1974692547_0.pdf"


###
# Validation tests for rule_ids 5.1 to 7.1-6, Author: Aran Moradi
###

def test_5_1_id_schema_missing_is_corrected():
    rule_id = "5-1"
    violation_name = "id-schema-missing"
    pdf_path = validation_pdf_path(PDF_FILENAME)

    assert verapdf_rule_count(pdf_path, rule_id) == 1

    with pikepdf.open(pdf_path) as pdf:
        detected_violations = detect_validation_violations(pdf_path, pdf, violation_name)
        assert len(detected_violations) == 1

        result_path = correct_validation_violations(
            pdf,
            detected_violations,
            "table_structure_FAILED_W1974692547_0_5_1_corrected.pdf",
            violation_name,
        )

    assert result_path.exists()
    assert verapdf_rule_count(result_path, rule_id) == 0


def test_7_1_5_not_mapped_to_standard_type_is_corrected():
    rule_id = "7.1-5"
    violation_name = "not-mapped-to-standard-type"
    pdf_path = validation_pdf_path(PDF_FILENAME)

    assert verapdf_rule_count(pdf_path, rule_id) == 1

    with pikepdf.open(pdf_path) as pdf:
        detected_violations = detect_validation_violations(pdf_path, pdf, violation_name)
        assert len(detected_violations) == 1

        result_path = correct_validation_violations(
            pdf,
            detected_violations,
            "table_structure_FAILED_W1974692547_0_7_1_5_corrected.pdf",
            violation_name,
        )

    assert result_path.exists()
    assert verapdf_rule_count(result_path, rule_id) == 0

# End Aran Moradi

###
# Validation tests for rule_ids 7.1-8 to 7.2-8, Author: Siju Li
###
def test_7_1_10_display_doc_title_false_is_corrected():
    rule_id = "7.1-10"
    violation_name = "display-doc-title-false"
    pdf_path = validation_pdf_path(PDF_FILENAME)
    assert verapdf_rule_count(pdf_path, rule_id) == 1
    with pikepdf.open(pdf_path) as pdf:
        detected_violations = detect_validation_violations(pdf_path, pdf, violation_name)
        assert len(detected_violations) == 1
        result_path = correct_validation_violations(
            pdf, detected_violations,
            "table_structure_FAILED_W1974692547_0_7_1_10_corrected.pdf",
            violation_name,
        )
    assert result_path.exists()
    assert verapdf_rule_count(result_path, rule_id) == 0
# End Siju Li

###
# Validation tests for rule_ids 7.2-9 to 7.2-21, Author: Robin Hart
###
# End Robin Hart

###
# Validation tests for rule_ids 7.2-22 to 7.2-34, Author: Riard Qupevaj
###

def test_7_2_33_FAILED_W1974692547_0_is_corrected():
    run_pdf_correction_test(
        pdf_path=validation_pdf_path(PDF_FILENAME),
        rule_id="7.2-33",
        violation_name="natural-language-metadata-undetermined",
        expected_count=1,
        output_filename="FAILED_W1974692547_0_7_2_33_corrected.pdf",
    )


def test_7_2_34_FAILED_W1974692547_0_is_corrected():
    run_pdf_correction_test(
        pdf_path=validation_pdf_path(PDF_FILENAME),
        rule_id="7.2-34",
        violation_name="natural-language-text-page-undetermined",
        expected_count=47,
        output_filename="FAILED_W1974692547_0_7_2_34_corrected.pdf",
    )

# End Riard Qupevaj

###
# Validation tests for rule_ids 7.2-36 to 7.4.4-3, Author: Brian Karle
###
# End Brian Karle

###
# Validation tests for rule_ids 7.5-1 to 7.18.1-3, Author: Florian Walcher
###
def test_invalid_annotation_W1974692547_is_corrected():
    run_pdf_correction_test(
        pdf_path=validation_pdf_path(
            PDF_FILENAME
        ),
        rule_id="7.18.1-2",
        violation_name="invalid-annotation",
        expected_count=4,
        output_filename=
            "table_structure_FAILED_W1974692547_corrected.pdf",
    )
# End Florian Walcher

###
# Validation tests for rule_ids 7.18.2-1 to 7.21.3.2-1, Author: Marwa Ayache
###
def test_7_18_5_1_link_annotation_artifact_not_nested_tag_link_is_corrected():
    rule_id = "7.18.5-1"
    violation_name = "link-annotation-artifact-not-nested-tag-link"
    pdf_path = validation_pdf_path(PDF_FILENAME)

    assert verapdf_rule_count(pdf_path, rule_id) == 2

    with pikepdf.open(pdf_path) as pdf:
        detected_violations = detect_validation_violations(pdf_path, pdf, violation_name)
        assert len(detected_violations) == 2

        result_path = correct_validation_violations(
            pdf,
            detected_violations,
            "table_structure_FAILED_W1974692547_0_7_18_5_1_corrected.pdf",
            violation_name,
        )

    assert result_path.exists()
    assert verapdf_rule_count(result_path, rule_id) == 0
# End Marwa Ayache

###
# Validation tests for rule_ids 7.21.3.3-1 to 7.21.8-1, Author: Babett Ludwig
###
def test_font_program_embedded_W1974692547_is_corrected():

    run_pdf_correction_test(
        pdf_path=validation_pdf_path(
            "table_structure_FAILED_W1974692547_0.pdf"
        ),
        rule_id="7.21.4.1-1",
        violation_name="font-program-embedded",
        expected_count=1,
        output_filename=
            "table_structure_FAILED_W1974692547_corrected.pdf",
    )
# End Babett Ludwig
