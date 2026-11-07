from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.pipeline_report.correction_run import CorrectionRun
from pdfaccessguru.model.pipeline_report.mapping_run import MappingRun
from pdfaccessguru.model.pipeline_report.phase_summary import PhaseSummary
from pdfaccessguru.model.pipeline_report.report_level import ReportLevel
from pdfaccessguru.model.pipeline_report.report_line import ReportLine
from pdfaccessguru.model.pipeline_report.report_phase import ReportPhase


@dataclass
class PipelineReport:
    """
    In-memory report for a single PDF pipeline run.

    Messages are grouped by pipeline phase. Detection-phase messages are
    further grouped per mapping invocation in :class:`MappingRun` entries.
    Correction-phase messages are further grouped per corrector invocation
    in :class:`CorrectionRun` entries.
    """

    pdf_path: str
    output_path: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    phases: list[ReportPhase] = field(default_factory=list)
    # Document-level measurements, e.g. how much text is reachable for screen readers
    # in the input and in the output ("text_tagging_input", "text_tagging_output").
    document_metrics: dict[str, Any] = field(default_factory=dict)
    _current_phase: ReportPhase | None = field(default=None, repr=False, compare=False)
    _lines_target: list[ReportLine] = field(default_factory=list, repr=False, compare=False)

    def open_phase(self, name: str, stage: str | None = None, round: int | None = None) -> ReportPhase:
        phase = ReportPhase(name=name, stage=stage, round=round)
        self.phases.append(phase)
        self._current_phase = phase
        self._lines_target = phase.lines
        return phase

    def close_phase(self) -> None:
        self._current_phase = None
        self._lines_target = []

    def open_correction(self, violation_name: str, affected_element: str, page: int | None = None) -> CorrectionRun:
        if self._current_phase is None:
            raise RuntimeError("Cannot open a correction scope without an active phase.")
        correction = CorrectionRun(
            violation_name=violation_name,
            affected_element=affected_element,
            page=page,
        )
        self._current_phase.corrections.append(correction)
        self._lines_target = correction.lines
        return correction

    def close_correction(self) -> None:
        if self._current_phase is not None:
            self._lines_target = self._current_phase.lines
        else:
            self._lines_target = []

    def open_mapping(self, violation_id: str, context: str) -> MappingRun:
        if self._current_phase is None:
            raise RuntimeError("Cannot open a mapping scope without an active phase.")
        mapping = MappingRun(
            violation_id=violation_id,
            context=context,
        )
        self._current_phase.mappings.append(mapping)
        self._lines_target = mapping.lines
        return mapping

    def close_mapping(self) -> None:
        if self._current_phase is not None:
            self._lines_target = self._current_phase.lines
        else:
            self._lines_target = []

    def set_phase_summary(self, violations: list[DetectedViolation]) -> None:
        if self._current_phase is None:
            return

        from pdfaccessguru.pipeline.reporting.summary import build_phase_summary

        detection_summary: PhaseSummary | None = None
        if self._current_phase.name == "verification":
            for phase in self.phases:
                if phase.name == "detection" and phase.summary is not None:
                    detection_summary = phase.summary
                    break

        self._current_phase.summary = build_phase_summary(
            violations,
            phase_name=self._current_phase.name,
            detection_summary=detection_summary,
        )

    def append(
        self,
        level: ReportLevel,
        message: str,
        context: str | None = None,
        image_png_base64: str | None = None,
        page: int | None = None,
    ) -> None:
        """Append a leveled message to the current phase or correction scope."""
        self._lines_target.append(
            ReportLine(level=level, message=message, context=context, image_png_base64=image_png_base64, page=page)
        )

    def mark_finished(self) -> None:
        self.finished_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        from pdfaccessguru.pipeline.reporting.summary import count_reporting_levels

        return {
            "pdf_path": self.pdf_path,
            "output_path": self.output_path,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "reporting": count_reporting_levels(self),
            "document_metrics": self.document_metrics,
            "phases": [phase.to_dict() for phase in self.phases],
        }
