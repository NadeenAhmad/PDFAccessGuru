from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pdfaccessguru.model.pipeline_report.report_line import ReportLine


@dataclass
class CorrectionRun:
    """Messages produced during one corrector invocation."""

    violation_name: str
    affected_element: str
    lines: list[ReportLine] = field(default_factory=list)
    # 1-based page number of the violation, if veraPDF's context names a page.
    page: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "violation_name": self.violation_name,
            "affected_element": self.affected_element,
            "page": self.page,
            "lines": [line.to_dict() for line in self.lines],
        }
