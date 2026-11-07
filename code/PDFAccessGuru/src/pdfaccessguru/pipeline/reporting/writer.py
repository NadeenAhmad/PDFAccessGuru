"""
Public write API for pipeline report messages.
"""

from __future__ import annotations

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.pipeline_report import ReportLevel
from pdfaccessguru.pipeline.reporting import console
from pdfaccessguru.pipeline.reporting.context import get_current_report


def _append(level: ReportLevel, message: str) -> None:
    report = get_current_report()
    if report is None:
        return
    console.write_message(level, message)
    report.append(level, message)


def report_debug(message: str) -> None:
    """Append a debug-level message to the current report scope."""
    _append(ReportLevel.DEBUG, message)


def report_info(message: str) -> None:
    """Append an info-level message to the current report scope."""
    _append(ReportLevel.INFO, message)


def report_warn(message: str) -> None:
    """Append a warning-level message to the current report scope."""
    _append(ReportLevel.WARN, message)


def report_error(message: str) -> None:
    """Append an error-level message to the current report scope."""
    _append(ReportLevel.ERROR, message)


def report_review(message: str, *, context: str | None = None, image_png: bytes | None = None,
                  page: int | None = None) -> None:
    """
    Record a value that was written into the PDF but should be checked by the author,
    e.g. a fallback text, a guessed language or a generic description. Correctors call
    this whenever their result is not certain; reports list these items separately
    instead of counting them as plain corrections.

    context:   text the reviewer can compare the value with (caption, nearby text), so the
               check also works without seeing the page.
    image_png: picture of the element (e.g. the figure), shown to sighted reviewers.
    page:      1-based page of the element, when the corrector knows it (veraPDF often does not).
    """
    report = get_current_report()
    if report is None:
        return
    console.write_message(ReportLevel.REVIEW, message)
    report.append(ReportLevel.REVIEW, message, context=context, image_png_base64=_small_png_base64(image_png),
                  page=page)


def _small_png_base64(image_png: bytes | None, max_side: int = 480) -> str | None:
    """Downscale a PNG for the report and return it base64-encoded (None if unusable)."""
    if not image_png:
        return None
    try:
        import base64
        import io

        from PIL import Image as PillowImage

        with PillowImage.open(io.BytesIO(image_png)) as image:
            image.thumbnail((max_side, max_side))
            buffer = io.BytesIO()
            image.convert("RGB").save(buffer, format="PNG", optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception:
        return None


def report_document_metric(name: str, value: object) -> None:
    """Store a document-level measurement (e.g. text tagging of input and output) in the report."""
    report = get_current_report()
    if report is None:
        return
    report.document_metrics[name] = value


def report_phase_summary(violations: list[DetectedViolation]) -> None:
    """
    Record violation summary metrics for the current pipeline phase.

    Intended for the detection and verification phases. Metrics are derived
    from the provided detected violations. Verification additionally records
    correction statistics using the detection phase summary as baseline.

    If no report session is active, this is a no-op.
    """
    report = get_current_report()
    if report is None:
        return
    report.set_phase_summary(violations)
