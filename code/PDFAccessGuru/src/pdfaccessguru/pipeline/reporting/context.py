"""
ContextVar-based session management for pipeline reports.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator

from pdfaccessguru.model.pipeline_report import PipelineReport

_current_report: ContextVar[PipelineReport | None] = ContextVar("pipeline_report", default=None)


def get_current_report() -> PipelineReport | None:
    """
    Return the active pipeline report for the current context.

    Writers and scope managers call this to resolve the report tree. When no
    ``pipeline_report_session`` is active, returns ``None`` and callers no-op
    silently.

    Returns:
        The active :class:`~pdfaccessguru.model.pipeline_report.PipelineReport`, or
        ``None`` if no session is active.
    """
    return _current_report.get()


@contextmanager
def pipeline_report_session(pdf_path: str, output_path: str) -> Iterator[dict[str, Any]]:
    """
    Open a reporting session for one pipeline run.

    Creates a :class:`~pdfaccessguru.model.pipeline_report.PipelineReport`, binds it to
    the current async/task context via a :class:`contextvars.ContextVar`, and
    yields an empty result dictionary for the duration of the ``with`` block.
    On exit, marks the report as finished, serializes it into that dictionary,
    and resets the context variable.

    Arguments:
        pdf_path: Path to the input PDF being processed.
        output_path: Path where the processed PDF will be saved.

    Yields:
        A report dictionary that is empty during the session and populated when
        the ``with`` block completes.
    """
    report = PipelineReport(pdf_path=pdf_path, output_path=output_path)
    result: dict[str, Any] = {}
    token = _current_report.set(report)
    try:
        yield result
    finally:
        report.mark_finished()
        result.clear()
        result.update(report.to_dict())
        _current_report.reset(token)
