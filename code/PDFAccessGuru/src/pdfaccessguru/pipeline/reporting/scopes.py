"""
Scope context managers that structure the pipeline report.

Each manager updates the active phase, mapping scope, or correction scope
for the duration of a ``with`` block. Typical nesting during detection or
verification is ``report_phase`` → ``report_mapping``. During correction it is
``report_phase`` → ``report_correction``.

If no ``pipeline_report_session`` is active, every scope manager is a no-op.
"""

from __future__ import annotations

import re

from contextlib import contextmanager
from typing import Iterator

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.reporting.context import get_current_report
from pdfaccessguru.utils.describers import describe_pikepdf_element

_MAPPING_PHASES = frozenset({"detection", "verification", "correction"})


@contextmanager
def report_phase(phase_name: str, stage: str | None = None, round: int | None = None) -> Iterator[None]:
    """
    Open a pipeline phase section in the report.

    Pushes a phase entry onto the report for the duration of the ``with`` block.
    If no report session is active, this is a no-op.
    """
    report = get_current_report()
    if report is None:
        yield
        return

    report.open_phase(phase_name, stage=stage, round=round)
    try:
        yield
    finally:
        report.close_phase()


@contextmanager
def report_mapping(verapdf_violation: VeraPdfViolation) -> Iterator[None]:
    """
    Open a veraPDF violation mapping section in the report.

    Creates one :class:`~pdfaccessguru.model.pipeline_report.MappingRun` for the
    mapping invocation. Active during the detection and verification phases.
    If no report session is active, or the current phase does not use mapping
    scopes, this is a no-op.
    """
    report = get_current_report()
    if (
        report is None
        or report._current_phase is None
        or report._current_phase.name not in _MAPPING_PHASES
    ):
        yield
        return

    report.open_mapping(verapdf_violation.rule_id, verapdf_violation.context)
    try:
        yield
    finally:
        report.close_mapping()


@contextmanager
def report_correction(detected_violation: DetectedViolation) -> Iterator[None]:
    """
    Open a violation correction section in the report.

    Creates one :class:`~pdfaccessguru.model.pipeline_report.CorrectionRun` for the
    corrector invocation. If no report session is active, this is a no-op.
    """
    report = get_current_report()
    if report is None:
        yield
        return

    violation_name = detected_violation.violation.name
    affected_element = describe_pikepdf_element(detected_violation.affected_element)
    page_match = re.search(r"(?:^|/)pages\[(\d+)\]", detected_violation.source_context or "")
    page = int(page_match.group(1)) + 1 if page_match else None
    report.open_correction(violation_name, affected_element, page)
    try:
        yield
    finally:
        report.close_correction()
