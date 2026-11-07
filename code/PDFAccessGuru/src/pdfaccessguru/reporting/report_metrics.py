from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import NOT_CORRECTED_ON_PURPOSE
from pdfaccessguru.reporting.taxonomy_loader import TaxonomyEntry, get_taxonomy_entry


@dataclass(frozen=True)
class ViolationMetric:
    name: str
    detected_count: int
    corrected_count: int
    remaining_count: int
    correction_rate: float
    taxonomy_entry: TaxonomyEntry | None
    # Occurrences found in the output that were not in the input (e.g. exposed by a repair).
    new_count: int = 0


@dataclass(frozen=True)
class ReportMetrics:
    input_path: str
    output_path: str
    started_at: str
    finished_at: str
    detected_count: int
    corrected_count: int
    remaining_count: int
    correction_rate: float
    warnings_count: int
    errors_count: int
    violation_metrics: list[ViolationMetric]
    # True when the final veraPDF check reports no PDF/UA-1 violation.
    passes_verapdf: bool = False
    # (violation name, message) of every value written that the author should check.
    review_items: tuple[tuple[str, str], ...] = ()
    # violation name -> number of occurrences deliberately left uncorrected (switched-off fix).
    not_corrected_on_purpose: dict[str, int] | None = None
    # Text reachable for screen readers before and after correction (see pipeline/text_tagging.py).
    text_tagging_input: dict[str, Any] | None = None
    text_tagging_output: dict[str, Any] | None = None
    # Colour contrast of the text (Phase 9, see pipeline/contrast.py), None if not measured.
    contrast: dict[str, Any] | None = None
    # Meaning and structure beyond the automatic check (Phase 10, see pipeline/meaning.py).
    meaning: dict[str, Any] | None = None


def build_report_metrics(report: dict[str, Any]) -> ReportMetrics:
    detection_summary = _phase_summary(report, "detection")
    verification_summary = _phase_summary(report, "verification")
    reporting_counts = report.get("reporting", {})

    detected_by_name = dict(detection_summary.get("violations_by_name", {}))
    remaining_by_name = dict(verification_summary.get("violations_by_name", {}))
    corrected_by_name = dict(verification_summary.get("corrected_by_name", {}))

    detected_count = int(detection_summary.get("total_detected_violations", 0))
    remaining_count = int(verification_summary.get("total_detected_violations", 0))
    # Never negative: if repairs exposed new problems, they show up as "new" per problem type.
    corrected_count = max(
        int(
            verification_summary.get(
                "total_corrected_violations",
                max(detected_count - remaining_count, 0),
            )
        ),
        0,
    )

    violation_names = sorted(set(detected_by_name) | set(remaining_by_name) | set(corrected_by_name))
    violation_metrics = [
        _build_violation_metric(
            name,
            detected_by_name=detected_by_name,
            remaining_by_name=remaining_by_name,
            corrected_by_name=corrected_by_name,
        )
        for name in violation_names
    ]

    return ReportMetrics(
        input_path=str(report.get("pdf_path", "")),
        output_path=str(report.get("output_path", "")),
        started_at=str(report.get("started_at", "")),
        finished_at=str(report.get("finished_at", "")),
        detected_count=detected_count,
        corrected_count=corrected_count,
        remaining_count=remaining_count,
        correction_rate=_ratio(corrected_count, detected_count),
        warnings_count=int(reporting_counts.get("warn", 0)),
        errors_count=int(reporting_counts.get("error", 0)),
        violation_metrics=violation_metrics,
        passes_verapdf=bool(verification_summary) and remaining_count == 0,
        review_items=_review_items(report),
        not_corrected_on_purpose=_not_corrected_on_purpose(report),
        text_tagging_input=report.get("document_metrics", {}).get("text_tagging_input"),
        text_tagging_output=report.get("document_metrics", {}).get("text_tagging_output"),
        contrast=report.get("document_metrics", {}).get("contrast"),
        meaning=report.get("document_metrics", {}).get("meaning"),
    )


def _correction_runs(report: dict[str, Any], first_round_only: bool = False):
    for phase in report.get("phases", []):
        if phase.get("name") != "correction":
            continue
        if first_round_only and phase.get("round", 1) != 1:
            continue
        yield from phase.get("corrections", [])


def _review_items(report: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    items = []
    for run in _correction_runs(report):
        for line in run.get("lines", []):
            if line.get("level") == "review":
                items.append((str(run.get("violation_name", "")), str(line.get("message", ""))))
    return tuple(items)


def _not_corrected_on_purpose(report: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    # Only the first round: later rounds see the same violations again.
    for run in _correction_runs(report, first_round_only=True):
        if any(str(line.get("message", "")).startswith(NOT_CORRECTED_ON_PURPOSE) for line in run.get("lines", [])):
            name = str(run.get("violation_name", ""))
            counts[name] = counts.get(name, 0) + 1
    return dict(sorted(counts.items()))


def _phase_summary(report: dict[str, Any], phase_name: str) -> dict[str, Any]:
    for phase in report.get("phases", []):
        if phase.get("name") == phase_name:
            return dict(phase.get("summary", {}))
    return {}


def _build_violation_metric(
    name: str,
    *,
    detected_by_name: dict[str, int],
    remaining_by_name: dict[str, int],
    corrected_by_name: dict[str, Any],
) -> ViolationMetric:
    detected_count = int(detected_by_name.get(name, 0))
    remaining_count = int(remaining_by_name.get(name, 0))
    correction_summary = corrected_by_name.get(name, {})
    corrected_count = int(
        correction_summary.get(
            "corrected_count",
            max(detected_count - remaining_count, 0),
        )
    )

    corrected_count = max(corrected_count, 0)
    return ViolationMetric(
        name=name,
        detected_count=detected_count,
        corrected_count=corrected_count,
        remaining_count=remaining_count,
        correction_rate=_ratio(corrected_count, detected_count),
        taxonomy_entry=get_taxonomy_entry(name),
        new_count=max(remaining_count - detected_count, 0),
    )


def _ratio(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return value / total
