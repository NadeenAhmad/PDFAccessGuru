from pdfaccessguru.model.pipeline_report import PhaseSummary
from pdfaccessguru.pipeline.reporting.summary import (
    build_detection_phase_summary,
    build_verification_phase_summary,
    count_violations_by_name,
)

from test.pipeline.reporting.conftest import make_detected_violation


def test_count_violations_by_name_empty():
    assert count_violations_by_name([]) == {}


def test_count_violations_by_name_groups_and_sorts():
    violations = [
        make_detected_violation(violation={"name": "b-violation"}),
        make_detected_violation(violation={"name": "a-violation"}),
        make_detected_violation(violation={"name": "a-violation"}),
    ]

    assert count_violations_by_name(violations) == {
        "a-violation": 2,
        "b-violation": 1,
    }


def test_build_detection_phase_summary():
    violations = [
        make_detected_violation(violation={"name": "alpha"}),
        make_detected_violation(violation={"name": "beta"}),
        make_detected_violation(violation={"name": "alpha"}),
    ]

    summary = build_detection_phase_summary(violations)

    assert summary == PhaseSummary(
        total_detected_violations=3,
        total_distinct_violations=2,
        violation_names=["alpha", "beta"],
        violations_by_name={"alpha": 2, "beta": 1},
    )


def test_build_verification_phase_summary_includes_correction_metrics():
    detected = [
        make_detected_violation(violation={"name": "alpha"}),
        make_detected_violation(violation={"name": "alpha"}),
        make_detected_violation(violation={"name": "beta"}),
    ]
    remaining = [make_detected_violation(violation={"name": "alpha"})]

    detection_summary = build_detection_phase_summary(detected)
    verification_summary = build_verification_phase_summary(remaining, detection_summary)

    assert verification_summary.total_detected_violations == 1
    assert verification_summary.total_distinct_violations == 1
    assert verification_summary.violation_names == ["alpha"]
    assert verification_summary.violations_by_name == {"alpha": 1}
    assert verification_summary.total_corrected_violations == 2
    assert verification_summary.corrected_by_name is not None
    assert verification_summary.corrected_by_name["alpha"].corrected_count == 1
    assert verification_summary.corrected_by_name["alpha"].detected_count == 2
    assert verification_summary.corrected_by_name["alpha"].ratio == 0.5
    assert verification_summary.corrected_by_name["beta"].corrected_count == 1
    assert verification_summary.corrected_by_name["beta"].detected_count == 1
    assert verification_summary.corrected_by_name["beta"].ratio == 1.0
