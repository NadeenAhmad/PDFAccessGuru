from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pdfaccessguru.model.pipeline_report.report_line import ReportLine


@dataclass
class MappingRun:
    """Messages produced during one veraPDF violation mapping invocation."""

    violation_id: str
    context: str
    lines: list[ReportLine] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "context": self.context,
            "lines": [line.to_dict() for line in self.lines],
        }
