from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ViolationCorrectionSummary:
    """Correction statistics for one violation type during verification."""

    corrected_count: int
    detected_count: int
    ratio: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "corrected_count": self.corrected_count,
            "detected_count": self.detected_count,
            "ratio": self.ratio,
        }


@dataclass
class PhaseSummary:
    """Aggregated violation metrics for a detection or verification phase."""

    total_detected_violations: int
    total_distinct_violations: int
    violation_names: list[str]
    violations_by_name: dict[str, int] = field(default_factory=dict)
    total_corrected_violations: int | None = None
    corrected_by_name: dict[str, ViolationCorrectionSummary] | None = None
    contexts_by_name: dict[str, list[str]] | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "total_detected_violations": self.total_detected_violations,
            "total_distinct_violations": self.total_distinct_violations,
            "violation_names": self.violation_names,
            "violations_by_name": self.violations_by_name,
        }
        if self.total_corrected_violations is not None:
            result["total_corrected_violations"] = self.total_corrected_violations
        if self.corrected_by_name is not None:
            result["corrected_by_name"] = {
                name: summary.to_dict()
                for name, summary in sorted(self.corrected_by_name.items())
            }
        if self.contexts_by_name is not None:
            result["contexts_by_name"] = {
                name: contexts
                for name, contexts in sorted(self.contexts_by_name.items())
            }
        return result
