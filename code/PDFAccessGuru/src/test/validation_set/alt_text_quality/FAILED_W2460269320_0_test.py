import pikepdf

from test.validation_set.utils import (
    correct_validation_violations,
    detect_validation_violations,
    validation_pdf_path,
    verapdf_rule_count,
)
from test.validation_set.generic_validation_Set_test import run_pdf_correction_test


PDF_FILENAME = "alt_text_quality_FAILED_W2460269320_0.pdf"


###
# Validation tests for rule_ids 5.1 to 7.1-6, Author: Aran Moradi
###

def test_7_1_3_content_neither_artifact_nor_tagged_content_is_corrected():
    rule_id = "7.1-3"
    violation_name = "content-neither-artifact-nor-tagged-content"
    pdf_path = validation_pdf_path(PDF_FILENAME)

    assert verapdf_rule_count(pdf_path, rule_id) == 168

    with pikepdf.open(pdf_path) as pdf:
        detected_violations = detect_validation_violations(pdf_path, pdf, violation_name)
        assert len(detected_violations) == 168

        result_path = correct_validation_violations(
            pdf,
            detected_violations,
            "alt_text_quality_FAILED_W2460269320_0_7_1_3_corrected.pdf",
            violation_name,
        )

    assert result_path.exists()
    assert verapdf_rule_count(result_path, rule_id) == 0

# End Aran Moradi

###
# Validation tests for rule_ids 7.1-8 to 7.2-8, Author: Siju Li
###
def test_7_1_9_missing_metadata_stream_dc_title_is_corrected():
    rule_id = "7.1-9"
    violation_name = "missing-metadata-stream-dc-title"
    pdf_path = validation_pdf_path(PDF_FILENAME)
    assert verapdf_rule_count(pdf_path, rule_id) == 1
    with pikepdf.open(pdf_path) as pdf:
        detected_violations = detect_validation_violations(pdf_path, pdf, violation_name)
        assert len(detected_violations) == 1
        result_path = correct_validation_violations(
            pdf, detected_violations,
            "alt_text_quality_FAILED_W2460269320_0_7_1_9_corrected.pdf",
            violation_name,
        )
    assert result_path.exists()
    assert verapdf_rule_count(result_path, rule_id) == 0


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
            "alt_text_quality_FAILED_W2460269320_0_7_1_10_corrected.pdf",
            violation_name,
        )
    assert result_path.exists()
    assert verapdf_rule_count(result_path, rule_id) == 0
# End Siju Li

###
# Validation tests for rule_ids 7.2-9 to 7.2-21, Author: Robin Hart
###

def test_7_2_21_natural_language_actual_text_attribute_undefined_is_corrected():
    rule_id = "7.2-21"
    violation_name = "natural-language-actual-text-attribute-undefined"
    pdf_path = validation_pdf_path(PDF_FILENAME)

    assert verapdf_rule_count(pdf_path, rule_id) == 13

    with pikepdf.open(pdf_path) as pdf:
        detected_violations = detect_validation_violations(pdf_path, pdf, violation_name)
        assert len(detected_violations) == 13

        result_path = correct_validation_violations(
            pdf,
            detected_violations,
            "alt_text_quality_FAILED_W2460269320_0_7_2_21_corrected.pdf",
            violation_name,
        )

    assert result_path.exists()
    assert verapdf_rule_count(result_path, rule_id) == 0

# End Robin Hart

###
# Validation tests for rule_ids 7.2-22 to 7.2-34, Author: Riard Qupevaj
###

def test_7_2_22_FAILED_W2460269320_0_is_corrected():
    run_pdf_correction_test(
        pdf_path=validation_pdf_path(PDF_FILENAME),
        rule_id="7.2-22",
        violation_name="natural-language-alt-attribute-undefined",
        expected_count=1,
        output_filename="FAILED_W2460269320_0_7_2_22_corrected.pdf",
    )


def test_7_2_30_FAILED_W2460269320_0_is_corrected():
    run_pdf_correction_test(
        pdf_path=validation_pdf_path(PDF_FILENAME),
        rule_id="7.2-30",
        violation_name="natural-language-ActualText-span-undetermined",
        expected_count=1,
        output_filename="FAILED_W2460269320_0_7_2_30_corrected.pdf",
    )


def test_7_2_33_FAILED_W2460269320_0_is_corrected():
    run_pdf_correction_test(
        pdf_path=validation_pdf_path(PDF_FILENAME),
        rule_id="7.2-33",
        violation_name="natural-language-metadata-undetermined",
        expected_count=3,
        output_filename="FAILED_W2460269320_0_7_2_33_corrected.pdf",
    )


def test_7_2_34_FAILED_W2460269320_0_is_corrected():
    run_pdf_correction_test(
        pdf_path=validation_pdf_path(PDF_FILENAME),
        rule_id="7.2-34",
        violation_name="natural-language-text-page-undetermined",
        expected_count=318,
        output_filename="FAILED_W2460269320_0_7_2_34_corrected.pdf",
    )

# End Riard Qupevaj

###
# Validation tests for rule_ids 7.2-36 to 7.4.4-3, Author: Brian Karle
###
# End Brian Karle

###
# Validation tests for rule_ids 7.5-1 to 7.18.1-3, Author: Florian Walcher
###
# End Florian Walcher

###
# Validation tests for rule_ids 7.18.2-1 to 7.21.3.2-1, Author: Marwa Ayache
###
# End Marwa Ayache

###
# Validation tests for rule_ids 7.21.3.3-1 to 7.21.8-1, Author: Babett Ludwig
###
# End Babett Ludwig
