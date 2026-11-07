from __future__ import annotations

from enum import Enum


class ReportLevel(Enum):
    """
    Severity level for a single pipeline report entry.

    Values are serialized to JSON via ``level.value`` (e.g. ``"info"``).
    Used by ``pdfaccessguru.pipeline.reporting.writer`` when appending messages.
    """

    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
    # A value was written that the author should check (fallback text, guessed language, ...).
    REVIEW = "review"
