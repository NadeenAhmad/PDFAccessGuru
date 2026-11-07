"""Customer-facing and technical report rendering."""

from pdfaccessguru.reporting.customer_report import (
    build_customer_report_images,
    build_customer_report_markdown,
    build_customer_report_pdf,
)
from pdfaccessguru.reporting.report_metrics import build_report_metrics
from pdfaccessguru.reporting.technical_report import build_technical_report_markdown, build_technical_report_pdf
from pdfaccessguru.reporting.violation_reference import (
    VIOLATION_REFERENCE_FILENAME,
    build_violation_reference_markdown,
)

__all__ = [
    "build_customer_report_images",
    "build_customer_report_markdown",
    "build_customer_report_pdf",
    "build_report_metrics",
    "build_technical_report_markdown",
    "build_technical_report_pdf",
    "build_violation_reference_markdown",
    "VIOLATION_REFERENCE_FILENAME",
]
