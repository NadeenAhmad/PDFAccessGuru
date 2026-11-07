from __future__ import annotations

import datetime as dt_module
from collections.abc import Callable
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

import pdfaccessguru.model.pipeline_report.pipeline_report as pipeline_report_module
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.pipeline_report import PipelineReport
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory

FIXED_NOW = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
PDF_PATH = "/in/test.pdf"
OUTPUT_PATH = "/out/test.pdf"


class _FixedDatetime(dt_module.datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW


@pytest.fixture(autouse=True)
def fixed_datetime(monkeypatch):
    monkeypatch.setattr(pipeline_report_module, "datetime", _FixedDatetime)
    return FIXED_NOW


def make_verapdf_violation(**overrides) -> VeraPdfViolation:
    defaults = {
        "rule_id": "7.2-1",
        "clause": "7.2",
        "test_number": "1",
        "description": "Test rule description",
        "context": "root/document[0]",
        "message": "Test message",
    }
    defaults.update(overrides)
    return VeraPdfViolation(**defaults)


def make_detected_violation(**overrides) -> DetectedViolation:
    violation_defaults = {
        "category": ViolationCategory.SYNTAX,
        "name": "test-violation",
        "description": "Test violation description",
        "guidelines": ["7.2"],
    }
    violation_overrides = overrides.pop("violation", {})
    violation_defaults.update(violation_overrides)

    defaults = {
        "violation": Violation(**violation_defaults),
        "affected_element": MagicMock(),
        "supplementary_information": [],
    }
    defaults.update(overrides)
    return DetectedViolation(**defaults)


def build_expected_report(
    pdf_path: str,
    output_path: str,
    build_fn: Callable[[PipelineReport], None],
) -> PipelineReport:
    report = PipelineReport(pdf_path=pdf_path, output_path=output_path)
    build_fn(report)
    report.mark_finished()
    return report


def build_expected_report_dict(
    pdf_path: str,
    output_path: str,
    build_fn: Callable[[PipelineReport], None],
) -> dict:
    return build_expected_report(pdf_path, output_path, build_fn).to_dict()


@pytest.fixture
def collect_console_output(monkeypatch):
    from pdfaccessguru.pipeline.reporting import console

    lines: list[str] = []

    def _collect(line: str, *, flush: bool = False) -> None:
        lines.append(line)

    monkeypatch.setattr(console, "_print_fn", _collect)
    return lines


@pytest.fixture
def force_console_color(monkeypatch):
    from pdfaccessguru.pipeline.reporting import console

    monkeypatch.setattr(console, "_use_color", lambda: True)
