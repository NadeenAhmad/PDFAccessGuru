from __future__ import annotations

import pytest

from pdfaccessguru.model.pipeline_report import ReportLevel
from pdfaccessguru.pipeline.reporting import console


@pytest.mark.parametrize(
    ("level", "expected_prefix"),
    [
        (ReportLevel.DEBUG, "\033[2m\033[36m"),
        (ReportLevel.INFO, "\033[32m"),
        (ReportLevel.WARN, "\033[33m"),
        (ReportLevel.ERROR, "\033[31m"),
    ],
)
def test_format_message_colors_by_level(level, expected_prefix):
    message = "pipeline message"
    formatted = console.format_message(level, message, use_color=True)

    assert formatted.startswith(expected_prefix)
    assert formatted.endswith("\033[0m")
    assert message in formatted
    assert "[DEBUG]" not in formatted
    assert "[INFO]" not in formatted


def test_write_message_prints_message_only(collect_console_output, force_console_color):
    console.write_message(ReportLevel.INFO, "correction applied")

    assert len(collect_console_output) == 1
    assert collect_console_output[0] == console.format_message(
        ReportLevel.INFO,
        "correction applied",
        use_color=True,
    )
    assert "[INFO]" not in collect_console_output[0]


def test_write_message_respects_no_color(monkeypatch, collect_console_output):
    monkeypatch.setenv("NO_COLOR", "1")

    console.write_message(ReportLevel.WARN, "something went wrong")

    assert collect_console_output == ["something went wrong"]


def test_write_message_uses_print_fn_override(collect_console_output, force_console_color):
    console.write_message(ReportLevel.ERROR, "failed")

    assert collect_console_output == [
        console.format_message(ReportLevel.ERROR, "failed", use_color=True)
    ]
