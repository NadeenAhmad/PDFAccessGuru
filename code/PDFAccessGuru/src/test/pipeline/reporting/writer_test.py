from pdfaccessguru.model.pipeline_report import CorrectionRun, MappingRun, ReportLevel, ReportLine, ReportPhase
from pdfaccessguru.pipeline.reporting import console
from pdfaccessguru.pipeline.reporting.context import pipeline_report_session
from pdfaccessguru.pipeline.reporting.scopes import report_correction, report_mapping, report_phase
from pdfaccessguru.pipeline.reporting.writer import (
    report_debug,
    report_error,
    report_info,
    report_phase_summary,
    report_warn,
)
from pdfaccessguru.utils.describers import describe_pikepdf_element

import pytest

from test.pipeline.reporting.conftest import (
    OUTPUT_PATH,
    PDF_PATH,
    build_expected_report_dict,
    make_detected_violation,
    make_verapdf_violation,
)


def _empty_detection_summary() -> dict:
    return {
        "total_detected_violations": 0,
        "total_distinct_violations": 0,
        "violation_names": [],
        "violations_by_name": {},
    }


def _detection_summary(violations: list) -> dict:
    from pdfaccessguru.pipeline.reporting.summary import build_detection_phase_summary

    return build_detection_phase_summary(violations).to_dict()


def test_report_levels_noop_without_session(collect_console_output):
    report_debug("debug")
    report_info("info")
    report_warn("warn")
    report_error("error")

    assert collect_console_output == []


def test_report_levels_print_to_console_with_session(collect_console_output, force_console_color):
    with pipeline_report_session(PDF_PATH, OUTPUT_PATH):
        with report_phase("detection"):
            report_debug("debug message")
            report_info("info message")
            report_warn("warn message")
            report_error("error message")

    assert collect_console_output == [
        console.format_message(ReportLevel.DEBUG, "debug message", use_color=True),
        console.format_message(ReportLevel.INFO, "info message", use_color=True),
        console.format_message(ReportLevel.WARN, "warn message", use_color=True),
        console.format_message(ReportLevel.ERROR, "error message", use_color=True),
    ]


def test_report_levels_in_phase():
    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            report_debug("debug message")
            report_info("info message")
            report_warn("warn message")
            report_error("error message")

    def _build_expected(report):
        report.open_phase("detection")
        report.append(ReportLevel.DEBUG, "debug message")
        report.append(ReportLevel.INFO, "info message")
        report.append(ReportLevel.WARN, "warn message")
        report.append(ReportLevel.ERROR, "error message")
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_report_levels_in_nested_scope():
    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            report_info("inside detection")

    def _build_expected(report):
        report.open_phase("detection")
        report.append(ReportLevel.INFO, "inside detection")
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_report_phase_summary_empty_detected():
    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            report_phase_summary([])

    def _build_expected(report):
        report.open_phase("detection")
        report.set_phase_summary([])
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected
    assert actual["phases"][0]["summary"] == _empty_detection_summary()


def test_report_phase_summary_with_violations():
    detected = [make_detected_violation()]

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            report_phase_summary(detected)

    def _build_expected(report):
        report.open_phase("detection")
        report.set_phase_summary(detected)
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected
    assert actual["phases"][0]["summary"] == _detection_summary(detected)


def test_report_phase_summary_remaining():
    detected = [
        make_detected_violation(violation={"name": "alpha"}),
        make_detected_violation(violation={"name": "alpha"}),
        make_detected_violation(violation={"name": "beta"}),
    ]
    remaining = [
        make_detected_violation(violation={"name": "alpha"}),
        make_detected_violation(violation={"name": "beta"}),
    ]

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            report_phase_summary(detected)
        with report_phase("verification"):
            report_phase_summary(remaining)

    def _build_expected(report):
        report.open_phase("detection")
        report.set_phase_summary(detected)
        report.close_phase()
        report.open_phase("verification")
        report.set_phase_summary(remaining)
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected

    verification_summary = actual["phases"][1]["summary"]
    assert verification_summary["total_detected_violations"] == 2
    assert verification_summary["total_corrected_violations"] == 1
    assert verification_summary["corrected_by_name"]["alpha"]["corrected_count"] == 1
    assert verification_summary["corrected_by_name"]["alpha"]["ratio"] == 0.5
    assert verification_summary["corrected_by_name"]["beta"]["corrected_count"] == 0
    assert verification_summary["corrected_by_name"]["beta"]["ratio"] == 0.0
    assert verification_summary["contexts_by_name"] == {}


def test_report_phase_summary_remaining_includes_source_contexts():
    detected = [
        make_detected_violation(
            violation={"name": "alpha"},
            source_context="root/document[0]/pages[0](3 0 obj PDPage)",
        ),
        make_detected_violation(
            violation={"name": "alpha"},
            source_context="root/document[0]/pages[2](8 0 obj PDPage)",
        ),
    ]

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            report_phase_summary(detected)
        with report_phase("verification"):
            report_phase_summary(detected)

    assert actual["phases"][-1]["summary"]["contexts_by_name"] == {
        "alpha": [
            "root/document[0]/pages[0](3 0 obj PDPage)",
            "root/document[0]/pages[2](8 0 obj PDPage)",
        ]
    }


def test_report_phase_summary_remaining_uses_first_detection_with_repeated_phases():
    detected = [
        make_detected_violation(violation={"name": "alpha"}),
        make_detected_violation(violation={"name": "alpha"}),
        make_detected_violation(violation={"name": "beta"}),
    ]
    after_first_pass = [
        make_detected_violation(violation={"name": "alpha"}),
        make_detected_violation(violation={"name": "beta"}),
    ]
    remaining = [
        make_detected_violation(violation={"name": "beta"}),
    ]

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            report_phase_summary(detected)
        with report_phase("correction"):
            pass
        with report_phase("detection"):
            report_phase_summary(after_first_pass)
        with report_phase("correction"):
            pass
        with report_phase("verification"):
            report_phase_summary(remaining)

    verification_summary = actual["phases"][-1]["summary"]
    assert verification_summary["total_detected_violations"] == 1
    assert verification_summary["total_corrected_violations"] == 2
    assert verification_summary["corrected_by_name"]["alpha"]["corrected_count"] == 2
    assert verification_summary["corrected_by_name"]["alpha"]["detected_count"] == 2
    assert verification_summary["corrected_by_name"]["beta"]["corrected_count"] == 0
    assert verification_summary["corrected_by_name"]["beta"]["detected_count"] == 1


def test_mini_pipeline_structure():
    detected = make_detected_violation()
    violation = detected.violation

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as actual:
        with report_phase("detection"):
            report_phase_summary([detected])

        with report_phase("correction"):
            with report_correction(detected):
                report_info("correction applied")

    def _build_expected(report):
        report.open_phase("detection")
        report.set_phase_summary([detected])
        report.close_phase()

        report.open_phase("correction")
        report.open_correction(
            violation.name,
            describe_pikepdf_element(detected.affected_element),
        )
        report.append(ReportLevel.INFO, "correction applied")
        report.close_correction()
        report.close_phase()

    expected = build_expected_report_dict(PDF_PATH, OUTPUT_PATH, _build_expected)
    assert actual == expected


def test_report_line_to_dict():
    line = ReportLine(level=ReportLevel.INFO, message="hello")
    assert line.to_dict() == {"level": "info", "message": "hello"}


def test_correction_run_to_dict():
    correction = CorrectionRun(
        violation_name="test-violation",
        affected_element="/Page keys=['/Type', '/Contents']",
        lines=[ReportLine(level=ReportLevel.INFO, message="corrector ran")],
    )
    assert correction.to_dict() == {
        "violation_name": "test-violation",
        "affected_element": "/Page keys=['/Type', '/Contents']",
        "page": None,
        "lines": [{"level": "info", "message": "corrector ran"}],
    }


def test_mapping_run_to_dict():
    mapping = MappingRun(
        violation_id="7.2-1",
        context="root/document[0]",
        lines=[ReportLine(level=ReportLevel.WARN, message="mapping failed")],
    )
    assert mapping.to_dict() == {
        "violation_id": "7.2-1",
        "context": "root/document[0]",
        "lines": [{"level": "warn", "message": "mapping failed"}],
    }


def test_report_phase_to_dict_includes_summary():
    from pdfaccessguru.model.pipeline_report import PhaseSummary

    phase = ReportPhase(
        name="detection",
        summary=PhaseSummary(
            total_detected_violations=3,
            total_distinct_violations=2,
            violation_names=["alpha", "beta"],
            violations_by_name={"alpha": 2, "beta": 1},
        ),
    )
    assert phase.to_dict() == {
        "name": "detection",
        "lines": [],
        "mappings": [],
        "summary": {
            "total_detected_violations": 3,
            "total_distinct_violations": 2,
            "violation_names": ["alpha", "beta"],
            "violations_by_name": {"alpha": 2, "beta": 1},
        },
    }


def test_report_phase_to_dict_includes_mappings():
    mapping = MappingRun(
        violation_id="7.2-1",
        context="root/document[0]",
        lines=[ReportLine(level=ReportLevel.WARN, message="mapping failed")],
    )
    phase = ReportPhase(name="detection", mappings=[mapping])
    assert phase.to_dict() == {
        "name": "detection",
        "lines": [],
        "mappings": [
            {
                "violation_id": "7.2-1",
                "context": "root/document[0]",
                "lines": [{"level": "warn", "message": "mapping failed"}],
            }
        ],
    }


def test_report_phase_to_dict_includes_mappings_for_verification():
    mapping = MappingRun(
        violation_id="7.2-1",
        context="root/document[0]",
        lines=[ReportLine(level=ReportLevel.WARN, message="mapping failed")],
    )
    phase = ReportPhase(name="verification", mappings=[mapping])
    assert phase.to_dict() == {
        "name": "verification",
        "lines": [],
        "mappings": [
            {
                "violation_id": "7.2-1",
                "context": "root/document[0]",
                "lines": [{"level": "warn", "message": "mapping failed"}],
            }
        ],
    }


@pytest.mark.parametrize(
    "writer",
    [report_debug, report_info, report_warn, report_error],
)
def test_report_writers_reject_extra_kwargs(writer):
    with pytest.raises(TypeError):
        writer("message", step="one")


def test_count_reporting_levels_across_nested_scopes():
    detected = make_detected_violation()
    verapdf_violation = make_verapdf_violation()

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as report:
        with report_phase("detection"):
            report_warn("phase warn")
            report_info("phase info")
            with report_mapping(verapdf_violation):
                report_debug("mapping debug")
                report_warn("mapping warn")
                report_error("mapping error")

        with report_phase("correction"):
            report_debug("phase debug")
            with report_correction(detected):
                report_warn("correction warn")
                report_debug("correction debug")

    assert report["reporting"] == {
        "debug": 3,
        "info": 1,
        "warn": 3,
        "error": 1,
        "review": 0,
    }


def test_pipeline_report_to_dict_includes_level_counts_at_top():
    detected = make_detected_violation()
    verapdf_violation = make_verapdf_violation()

    with pipeline_report_session(PDF_PATH, OUTPUT_PATH) as report:
        with report_phase("detection"):
            with report_mapping(verapdf_violation):
                report_warn("mapping warn")

        with report_phase("correction"):
            with report_correction(detected):
                report_debug("correction debug")

    assert list(report.keys())[:7] == [
        "pdf_path",
        "output_path",
        "started_at",
        "finished_at",
        "reporting",
        "document_metrics",
        "phases",
    ]
    assert report["reporting"] == {
        "debug": 1,
        "info": 0,
        "warn": 1,
        "error": 0,
        "review": 0,
    }
