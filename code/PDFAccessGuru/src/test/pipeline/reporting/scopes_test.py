from pdfaccessguru.model.pipeline_report import ReportLevel, ReportLine, ReportPhase
from pdfaccessguru.pipeline.reporting.context import pipeline_report_session
from pdfaccessguru.pipeline.reporting.scopes import report_correction, report_mapping, report_phase
from pdfaccessguru.pipeline.reporting.writer import report_info, report_warn
from pdfaccessguru.utils.describers import describe_pikepdf_element

from test.pipeline.reporting.conftest import (
    OUTPUT_PATH,
    PDF_PATH,
    build_expected_report_dict,
    make_detected_violation,
    make_verapdf_violation,
)


def test_report_phase_noop_without_session():
    with report_phase("detection"):
        report_info("should not appear")


def test_report_phase_detection():
    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            report_info("detected something")

    def _build_expected(report):
        report.open_phase("detection")
        report.append(ReportLevel.INFO, "detected something")
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_report_phase_unknown_name():
    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("custom"):
            pass

    def _build_expected(report):
        report.open_phase("custom")
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_report_correction():
    detected = make_detected_violation()

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("correction"):
            with report_correction(detected):
                pass

    violation = detected.violation

    def _build_expected(report):
        report.open_phase("correction")
        report.open_correction(
            violation.name,
            describe_pikepdf_element(detected.affected_element),
        )
        report.close_correction()
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_report_correction_with_messages():
    detected = make_detected_violation()
    violation_name = detected.violation.name

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("correction"):
            with report_correction(detected):
                report_info("corrector ran")

    def _build_expected(report):
        report.open_phase("correction")
        report.open_correction(
            violation_name,
            describe_pikepdf_element(detected.affected_element),
        )
        report.append(ReportLevel.INFO, "corrector ran")
        report.close_correction()
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_nested_detection_and_correction():
    detected = make_detected_violation()
    violation_name = detected.violation.name

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            report_info("start detect")
            report_info("end detect")

        with report_phase("correction"):
            with report_correction(detected):
                report_info("correction applied")

    def _build_expected(report):
        report.open_phase("detection")
        report.append(ReportLevel.INFO, "start detect")
        report.append(ReportLevel.INFO, "end detect")
        report.close_phase()

        report.open_phase("correction")
        report.open_correction(
            violation_name,
            describe_pikepdf_element(detected.affected_element),
        )
        report.append(ReportLevel.INFO, "correction applied")
        report.close_correction()
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_report_mapping():
    verapdf_violation = make_verapdf_violation()

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            with report_mapping(verapdf_violation):
                pass

    def _build_expected(report):
        report.open_phase("detection")
        report.open_mapping(verapdf_violation.rule_id, verapdf_violation.context)
        report.close_mapping()
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_report_mapping_with_messages():
    verapdf_violation = make_verapdf_violation()

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            with report_mapping(verapdf_violation):
                report_warn("mapping failed")

    def _build_expected(report):
        report.open_phase("detection")
        report.open_mapping(verapdf_violation.rule_id, verapdf_violation.context)
        report.append(ReportLevel.WARN, "mapping failed")
        report.close_mapping()
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_report_mapping_in_verification():
    verapdf_violation = make_verapdf_violation()

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("verification"):
            with report_mapping(verapdf_violation):
                report_warn("mapping failed")

    def _build_expected(report):
        report.open_phase("verification")
        report.open_mapping(verapdf_violation.rule_id, verapdf_violation.context)
        report.append(ReportLevel.WARN, "mapping failed")
        report.close_mapping()
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_report_mapping_is_recorded_in_correction_stages():
    # Since Phase 3 each correction stage locates its own violations, so mapping messages
    # belong to the stage's correction phase.
    verapdf_violation = make_verapdf_violation()

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("correction"):
            with report_mapping(verapdf_violation):
                report_warn("mapping failed")

    def _build_expected(report):
        report.open_phase("correction")
        report.open_mapping(verapdf_violation.rule_id, verapdf_violation.context)
        report.append(ReportLevel.WARN, "mapping failed")
        report.close_mapping()
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_report_mapping_noop_without_session():
    verapdf_violation = make_verapdf_violation()

    with report_mapping(verapdf_violation):
        report_warn("should not appear")
