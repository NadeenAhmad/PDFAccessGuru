"""
Aggregate reporting statistics for pipeline reports.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.pipeline_report import PipelineReport, ReportLevel, ReportLine
from pdfaccessguru.model.pipeline_report.phase_summary import PhaseSummary, ViolationCorrectionSummary


def iter_report_lines(report: PipelineReport) -> Iterator[ReportLine]:
    """Yield every report line across all phases and nested scopes."""
    for phase in report.phases:
        yield from phase.lines
        for mapping in phase.mappings:
            yield from mapping.lines
        for correction in phase.corrections:
            yield from correction.lines


def _name(violation: object) -> str:
    """Violation name of a DetectedViolation or of a raw veraPDF finding."""
    if hasattr(violation, "violation"):
        return violation.violation.name  # type: ignore[attr-defined]
    from pdfaccessguru.pipeline.PDFAccessGuruDetect.detect import violation_name

    return violation_name(violation.rule_id)  # type: ignore[attr-defined]


def _context(violation: object) -> str:
    return getattr(violation, "source_context", None) or getattr(violation, "context", "") or ""


def count_violations_by_name(violations: list) -> dict[str, int]:
    """
    Return how many violations exist for each violation name. Accepts DetectedViolations or raw
    veraPDF findings; summaries use the raw findings so that nothing that could not be mapped
    disappears from the counts.
    """
    counts = Counter(_name(violation) for violation in violations)
    return dict(sorted(counts.items()))


def build_detection_phase_summary(violations: list[DetectedViolation]) -> PhaseSummary:
    """Build violation metrics for the detection phase."""
    violations_by_name = count_violations_by_name(violations)
    return PhaseSummary(
        total_detected_violations=len(violations),
        total_distinct_violations=len(violations_by_name),
        violation_names=list(violations_by_name.keys()),
        violations_by_name=violations_by_name,
    )


def build_verification_phase_summary(
    remaining_violations: list[DetectedViolation],
    detection_summary: PhaseSummary,
) -> PhaseSummary:
    """Build violation metrics for the verification phase, including correction stats."""
    remaining_by_name = count_violations_by_name(remaining_violations)
    corrected_by_name: dict[str, ViolationCorrectionSummary] = {}
    contexts_by_name: dict[str, list[str]] = {}

    for violation in remaining_violations:
        context = _context(violation)
        if context:
            contexts_by_name.setdefault(_name(violation), []).append(context)

    for violation_name, detected_count in detection_summary.violations_by_name.items():
        remaining_count = remaining_by_name.get(violation_name, 0)
        corrected_count = detected_count - remaining_count
        ratio = corrected_count / detected_count if detected_count else 0.0
        corrected_by_name[violation_name] = ViolationCorrectionSummary(
            corrected_count=corrected_count,
            detected_count=detected_count,
            ratio=ratio,
        )

    total_corrected_violations = (
        detection_summary.total_detected_violations - len(remaining_violations)
    )

    return PhaseSummary(
        total_detected_violations=len(remaining_violations),
        total_distinct_violations=len(remaining_by_name),
        violation_names=list(remaining_by_name.keys()),
        violations_by_name=remaining_by_name,
        total_corrected_violations=total_corrected_violations,
        corrected_by_name=corrected_by_name,
        contexts_by_name=contexts_by_name,
    )


def build_phase_summary(
    violations: list[DetectedViolation],
    *,
    phase_name: str,
    detection_summary: PhaseSummary | None = None,
) -> PhaseSummary:
    """Build phase summary metrics from a list of detected violations."""
    if phase_name == "verification":
        if detection_summary is None:
            raise ValueError(
                "Verification phase summary requires the detection phase summary."
            )
        return build_verification_phase_summary(violations, detection_summary)
    return build_detection_phase_summary(violations)


def count_reporting_levels(report: PipelineReport) -> dict[str, int]:
    """
    Return total counts for every report level across the full report tree.

    Keys match :class:`~pdfaccessguru.model.pipeline_report.ReportLevel` values
    (``debug``, ``info``, ``warn``, ``error``).
    """
    counts = {level.value: 0 for level in ReportLevel}
    for line in iter_report_lines(report):
        counts[line.level.value] += 1
    return counts
