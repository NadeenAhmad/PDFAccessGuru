"""
Context-based reporting for the PDFAccessGuru pipeline.

Provides session management and message-writing helpers for building a
structured report during a single pipeline run. The public API exports
session and write functions via ``__all__``; scope context managers live in
``pdfaccessguru.pipeline.reporting.scopes`` and are imported from that submodule.
"""

from pdfaccessguru.pipeline.reporting.context import get_current_report, pipeline_report_session
from pdfaccessguru.pipeline.reporting.summary import count_reporting_levels, iter_report_lines
from pdfaccessguru.pipeline.reporting.writer import (
    report_debug,
    report_error,
    report_info,
    report_phase_summary,
    report_review,
    report_warn,
)

__all__ = [
    "count_reporting_levels",
    "get_current_report",
    "iter_report_lines",
    "pipeline_report_session",
    "report_debug",
    "report_error",
    "report_info",
    "report_phase_summary",
    "report_review",
    "report_warn",
]
