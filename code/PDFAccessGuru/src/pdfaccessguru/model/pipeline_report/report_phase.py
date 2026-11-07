from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pdfaccessguru.model.pipeline_report.correction_run import CorrectionRun
from pdfaccessguru.model.pipeline_report.mapping_run import MappingRun
from pdfaccessguru.model.pipeline_report.phase_summary import PhaseSummary
from pdfaccessguru.model.pipeline_report.report_line import ReportLine


@dataclass
class ReportPhase:
    """Messages and optional summary for one pipeline phase."""

    name: str
    lines: list[ReportLine] = field(default_factory=list)
    # For correction phases: which stage ran (see pipeline/stages.py) and in which round.
    stage: str | None = None
    round: int | None = None
    corrections: list[CorrectionRun] = field(default_factory=list)
    mappings: list[MappingRun] = field(default_factory=list)
    summary: PhaseSummary | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "lines": [line.to_dict() for line in self.lines],
        }
        if self.stage is not None:
            result["stage"] = self.stage
        if self.round is not None:
            result["round"] = self.round
        if self.name == "correction":
            result["corrections"] = self._convert_correction_dict()
        if self.name in ("detection", "verification") or (self.name == "correction" and self.mappings):
            result["mappings"] = self._convert_mapping_dict()
        if self.summary is not None:
            result["summary"] = self.summary.to_dict()
        return result

    def _convert_correction_dict(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for correction in self.corrections:
            if len(correction.lines) != 0:
                result.append(correction.to_dict())
        return result

    def _convert_mapping_dict(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for mapping in self.mappings:
            if len(mapping.lines) != 0:
                result.append(mapping.to_dict())
        return result