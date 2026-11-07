"""
Colored console output for pipeline report messages.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable

from pdfaccessguru.model.pipeline_report import ReportLevel

_RESET = "\033[0m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"

_LEVEL_PREFIXES = {
    ReportLevel.DEBUG: f"{_DIM}{_CYAN}",
    ReportLevel.INFO: _GREEN,
    ReportLevel.WARN: _YELLOW,
    ReportLevel.ERROR: _RED,
    ReportLevel.REVIEW: _YELLOW,
}

_print_fn: Callable[[str], None]


def _default_print(message: str, *, flush: bool = False) -> None:
    print(message, flush=flush)


_print_fn = _default_print

# The command line turns the mirror off by default (users see plain progress lines only);
# `pdfaccessguru fix --verbose` and developers keep it on.
_enabled = True


def set_console_output(enabled: bool) -> None:
    """Turn printing of report messages to the console on or off."""
    global _enabled
    _enabled = enabled


def _use_color() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if hasattr(sys.stdout, "isatty") and not sys.stdout.isatty():
        return False
    return True


def format_message(level: ReportLevel, message: str, *, use_color: bool | None = None) -> str:
    """
    Format a report message for console output.

    When color is enabled, wraps the message in ANSI codes by severity.
    The message text itself is never prefixed with level labels or metadata.
    """
    if use_color is None:
        use_color = _use_color()
    if not use_color:
        return message
    prefix = _LEVEL_PREFIXES[level]
    return f"{prefix}{message}{_RESET}"


def write_message(level: ReportLevel, message: str) -> None:
    """Print a leveled report message to the console."""
    if not _enabled:
        return
    _print_fn(format_message(level, message), flush=True)
