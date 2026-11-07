from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pdfaccessguru.model.pipeline_report.report_level import ReportLevel


@dataclass
class ReportLine:
    """A single leveled message in a phase or correction run."""

    level: ReportLevel
    message: str
    # Optional details for review items: text to compare the value with (e.g. a figure's
    # caption) and a small PNG of the element (base64), shown in the review list.
    context: str | None = None
    image_png_base64: str | None = None
    page: int | None = None              # 1-based page of the element, if the corrector knows it

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"level": self.level.value, "message": self.message}
        if self.context:
            result["context"] = self.context
        if self.image_png_base64:
            result["image_png_base64"] = self.image_png_base64
        if self.page:
            result["page"] = self.page
        return result
