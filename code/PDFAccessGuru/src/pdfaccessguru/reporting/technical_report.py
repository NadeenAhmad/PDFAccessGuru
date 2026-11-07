from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from datetime import datetime

from pdfaccessguru.reporting.report_metrics import build_report_metrics
from pdfaccessguru.reporting.pdf_report import render_report_pdf


def build_technical_report_markdown(report: dict[str, Any]) -> str:
    metrics = build_report_metrics(report)

    started = datetime.fromisoformat(metrics.started_at)
    finished = datetime.fromisoformat(metrics.finished_at)

    execution_time = (finished - started).total_seconds()
    lines = [
        "# Technical Pipeline Report",
        "",
        "## Files",
        "",
        f"- Input path: `{metrics.input_path}`",
        f"- Output path: `{metrics.output_path}`",
        f"- Input file: `{Path(metrics.input_path).name}`",
        f"- Output file: `{Path(metrics.output_path).name}`",
        f"- Started at: `{metrics.started_at}`",
        f"- Finished at: `{metrics.finished_at}`",
        f"- Execution Time: `{execution_time:.2f} seconds`",
        "",
        "## Pipeline Summary",
        "",
        f"- Detected violations: {metrics.detected_count}",
        f"- Corrected violations: {metrics.corrected_count}",
        f"- Remaining violations: {metrics.remaining_count}",
        f"- Correction rate: {metrics.correction_rate * 100:.1f}% (per occurrence; see note)",
        f"- Passes veraPDF PDF/UA-1: {'yes' if metrics.passes_verapdf else 'no'}",
        f"- Text operators tagged / artifact / untagged (input): {_tagging(metrics.text_tagging_input)}",
        f"- Text operators tagged / artifact / untagged (output): {_tagging(metrics.text_tagging_output)}",
        f"- Values flagged for review: {len(metrics.review_items)}",
        f"- Not corrected on purpose (switched-off correctors): {metrics.not_corrected_on_purpose or {}}",
        f"- Warnings: {metrics.warnings_count}",
        f"- Errors: {metrics.errors_count}",
        "",
        "Note: veraPDF reports one violation per failing check; a single document-level fix can remove",
        "thousands of occurrences. Compare documents by pass/fail and text tagging, not by correction rate.",
        "",
        "## Violation Metrics",
        "",
        "| Violation | Found | Corrected | Remaining | Rate | Category | Guideline | Rule |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]

    for violation in metrics.violation_metrics:
        entry = violation.taxonomy_entry
        lines.append(
            "| "
            f"{_escape_table(violation.name)} | "
            f"{violation.detected_count} | "
            f"{violation.corrected_count} | "
            f"{violation.remaining_count} | "
            f"{violation.correction_rate * 100:.1f}% | "
            f"{_escape_table(entry.category if entry else '')} | "
            f"{_escape_table(entry.guideline if entry else '')} | "
            f"{_escape_table(entry.rule if entry else '')} |"
        )

    lines.extend(["", "## Phase Details", ""])
    for phase in report.get("phases", []):
        lines.extend(_render_phase(phase))

    lines.extend(
        [
            "",
            "## Raw JSON Report",
            "",
            "```json",
            json.dumps(report, indent=2, ensure_ascii=False),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def build_technical_report_pdf(report: dict[str, Any]) -> bytes:
    return render_report_pdf(
        build_technical_report_markdown(report),
        "Technical Pipeline Report",
    )


def _render_phase(phase: dict[str, Any]) -> list[str]:
    phase_name = str(phase.get("name", "unknown"))
    lines = [f"### {phase_name.title()}", ""]
    summary = phase.get("summary")
    if summary:
        lines.extend(["Summary:", ""])
        for key, value in summary.items():
            if key in {"violation_names", "violations_by_name", "corrected_by_name"}:
                continue
            lines.append(f"- {key}: {value}")
        lines.append("")

    phase_lines = phase.get("lines", [])
    if phase_lines:
        lines.extend(["Messages:", ""])
        lines.extend(_render_report_lines(phase_lines))
        lines.append("")

    for mapping in phase.get("mappings", []):
        lines.append(f"- Mapping `{mapping.get('violation_id', '')}`")
        context = mapping.get("context", "")
        if context:
            lines.append(f"  - Context: `{context}`")
        lines.extend(f"  {line}" for line in _render_report_lines(mapping.get("lines", [])))

    for correction in phase.get("corrections", []):
        lines.append(f"- Correction `{correction.get('violation_name', '')}`")
        affected_element = correction.get("affected_element", "")
        if affected_element:
            lines.append(f"  - Affected element: `{affected_element}`")
        lines.extend(f"  {line}" for line in _render_report_lines(correction.get("lines", [])))

    lines.append("")
    return lines


def _render_report_lines(report_lines: list[dict[str, Any]]) -> list[str]:
    return [
        f"- `{line.get('level', '')}`: {line.get('message', '')}"
        for line in report_lines
    ]


def _tagging(tagging: dict[str, Any] | None) -> str:
    if not tagging:
        return "not measured"
    return (f"{tagging.get('tagged', 0)} / {tagging.get('artifact', 0)} / {tagging.get('untagged', 0)} "
            f"({tagging.get('tagged_share', 0.0) * 100:.1f}% tagged)")


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
