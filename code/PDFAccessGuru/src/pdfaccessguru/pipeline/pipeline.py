"""
The PDFAccessGuru pipeline: check, correct in stages, check again.

1. The file is checked once with veraPDF (the baseline for the report).
2. Corrections run stage by stage in the order defined in pipeline/stages.py, one rule at a
   time. After the fixes for a rule, the file is checked again; if the fixes made it worse
   (see pipeline/transaction.py) they are undone and the report says why.
3. This repeats (at most MAX_ROUNDS times) until a round changes nothing, because some
   problems only become visible after other repairs.
4. The corrected file is saved and checked a final time.

Counts in the report always come from veraPDF's findings, so problems that cannot be located
or have no automatic fix stay visible as "still open".
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from pathlib import Path
from threading import Event
from typing import Any

import pikepdf

from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correct import correct
from pdfaccessguru.pipeline.PDFAccessGuruDetect.detect import map_violations
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.pipeline.reporting.context import pipeline_report_session
from pdfaccessguru.pipeline.reporting.scopes import report_phase
from pdfaccessguru.pipeline.meaning import MeaningResult
from pdfaccessguru.pipeline.reporting.writer import (
    report_debug,
    report_document_metric,
    report_info,
    report_phase_summary,
    report_warn,
)
from pdfaccessguru.LLM.fallback import start_run as start_ai_run
from pdfaccessguru.pipeline.protection import start_run as start_protection_run
from pdfaccessguru.pipeline.stages import STAGES, Stage, ordered_rules, page_of_context
from pdfaccessguru.pipeline.text_tagging import measure_text_tagging
from pdfaccessguru.pipeline.transaction import judge_together, WorkingDocument, judge_fix
from pdfaccessguru.utils import verify_pdf_path

MAX_ROUNDS = 3

# Receives a short plain-language text ("Fixing fonts and characters") and the progress (0..1).
ProgressCallback = Callable[[str, float], None]


def run_pipeline(
    pdf_path: str,
    output_path: str,
    progress_callback: ProgressCallback | None = None,
    cancel_event: Event | None = None,
    owner_password: str | None = None,
    fix_contrast: bool = False,
) -> dict[str, Any]:
    """
    Check and correct the PDF at pdf_path and save the result at output_path.
    The input file is never changed. Returns the structured report of the run.
    fix_contrast: also change text colours that are too close to their background (off by
    default: many templates must keep their colours). The contrast is reported either way.
    """
    verify_pdf_path(pdf_path)
    if Path(output_path).resolve() == Path(pdf_path).resolve():
        raise ValueError("The corrected file must not replace the original file.")
    progress = _Progress(progress_callback)
    _raise_if_cancelled(cancel_event)

    with pipeline_report_session(pdf_path, output_path) as report_dict:
        start_protection_run(owner_password)        # only kept in memory for this run
        document = WorkingDocument.open(pdf_path)
        meaning = MeaningResult()
        try:
            report_document_metric("text_tagging_input", measure_text_tagging(document.pdf))
            _clear_empty_descriptions(document, meaning)
            with tempfile.TemporaryDirectory(prefix="pdfaccessguru-") as work:
                check_path = str(Path(work) / "check.pdf")

                progress("Checking the file", 0.02)
                with report_phase("detection"):
                    document.save(check_path)
                    findings = run_verapdf(check_path, cancel_event)
                    report_debug(f"veraPDF found {len(findings)} problem(s).")
                    report_phase_summary(findings)
                    start_ai_run()                     # which AI writes texts, or the "no AI" note

                _correct_in_stages(document, findings, check_path, progress, cancel_event)
                progress("Checking meaning and structure", 0.92)
                with report_phase("meaning"):
                    _check_meaning(document, meaning)
                progress("Checking the colour contrast", 0.94)
                with report_phase("contrast"):
                    _check_contrast(document, fix_contrast)
                document.save(output_path)
        finally:
            document.close()

        progress("Final check", 0.97)
        _raise_if_cancelled(cancel_event)
        with report_phase("verification"):
            remaining = run_verapdf(output_path, cancel_event)
            report_phase_summary(remaining)
            with pikepdf.open(output_path) as corrected:
                report_document_metric("text_tagging_output", measure_text_tagging(corrected))
        progress("Done", 1.0)
        return report_dict


def _clear_empty_descriptions(document: WorkingDocument, meaning: "MeaningResult") -> None:
    """Before the fixes: descriptions that say nothing are removed, so the normal fix writes real ones."""
    from pdfaccessguru.pipeline.meaning import clear_empty_descriptions

    try:
        clear_empty_descriptions(document.pdf, meaning)
    except Exception as error:
        report_debug(f"Picture descriptions could not be checked: {error}")


def _check_meaning(document: WorkingDocument, meaning: "MeaningResult") -> None:
    """Problems with meaning and structure that the PDF/UA check cannot see (Phase 10)."""
    from pdfaccessguru.pipeline.meaning import check_meaning

    try:
        if isinstance(document.pdf.Root.get("/StructTreeRoot"), pikepdf.Dictionary):
            check_meaning(document.pdf, meaning)
    except Exception as error:                     # these checks must never stop the fixing
        report_debug(f"Meaning and structure could not be checked: {error}")
    report_document_metric("meaning", meaning.as_dict())
    if meaning.language_parts:
        report_info(f"The language of {meaning.language_parts} passage(s) was set: "
                    + ", ".join(f"{lang} ({n})" for lang, n in meaning.languages.items()) + ".")


def _check_contrast(document: WorkingDocument, fix: bool) -> None:
    """Colour contrast of the text (Phase 9): always measured; changed only if the user switched it on."""
    from pdfaccessguru.pipeline.contrast import check_and_fix_contrast

    try:
        result = check_and_fix_contrast(document, fix)
    except Exception as error:                     # measuring contrast must never stop the fixing
        report_debug(f"The colour contrast could not be checked: {error}")
        return
    report_document_metric("contrast", result.as_dict())
    if result.undone:
        report_warn(f"The colour changes were undone: {result.undone}.")
    elif result.fixed:
        report_info(f"Colour contrast: {result.fixed} place(s) with too little contrast got a darker or lighter text colour.")


def _correct_in_stages(
    document: WorkingDocument,
    findings: list[VeraPdfViolation],
    check_path: str,
    progress: "_Progress",
    cancel_event: Event | None,
) -> list[VeraPdfViolation]:
    """Run the stages until a round changes nothing. Returns the findings after the last kept fix."""
    last_attempt: dict[str, int] = {}   # rule -> number of findings when it was last tried
    tried_alone: set[str] = set()       # rules whose combined fix was undone: one by one from now on
    for round_number in range(1, MAX_ROUNDS + 1):
        changed = False
        for index, stage in enumerate(STAGES):
            while True:
                # Recomputed after every fix: a fix can reveal problems of this stage.
                counts = _counts(findings)
                pending = [rule for rule in ordered_rules(stage, [r for r in counts if stage.contains(r)])
                           if last_attempt.get(rule) != counts[rule]]
                if not pending:
                    break
                rule_id = pending[0]
                _raise_if_cancelled(cancel_event)
                suffix = "" if round_number == 1 else " (checking again)"
                progress(stage.label + suffix, 0.05 + 0.9 * index / len(STAGES))

                # Whole-document fixes of this stage are tried together with one check; if the
                # check fails they are undone and tried one by one (Phase 5: fewer veraPDF runs).
                batch = [rule for rule in pending if _batchable(stage, rule) and rule not in tried_alone]
                if len(batch) > 1 and rule_id in batch:
                    for rule in batch:
                        last_attempt[rule] = counts[rule]
                    with report_phase("correction", stage=stage.name, round=round_number):
                        after, outcome = _try_rules_together(document, stage, batch, findings, check_path, cancel_event)
                    if outcome == "kept":
                        changed = changed or _counts(after) != _counts(findings)
                        findings = after
                    elif outcome == "undone":           # try them one by one
                        for rule in batch:
                            last_attempt.pop(rule, None)
                        tried_alone.update(batch)
                    continue

                group = [f for f in findings if f.rule_id == rule_id]
                last_attempt[rule_id] = len(group)
                with report_phase("correction", stage=stage.name, round=round_number):
                    after = _try_rule(document, stage, rule_id, group, findings, check_path, cancel_event)
                if after is not None:
                    changed = changed or _counts(after) != _counts(findings)
                    findings = after
        if not changed:
            break
    return findings


def _try_rule(
    document: WorkingDocument,
    stage: Stage,
    rule_id: str,
    group: list[VeraPdfViolation],
    findings: list[VeraPdfViolation],
    check_path: str,
    cancel_event: Event | None,
) -> list[VeraPdfViolation] | None:
    """
    Correct all findings of one rule as one unit. Returns the new findings if the fixes are
    kept, or None if nothing was tried or the fixes were undone.
    """
    snapshot = document.snapshot()
    detected = map_violations(_select_for_correction(stage, rule_id, group), document.pdf, cancel_event)
    if correct(detected, document.pdf, cancel_event) == 0:
        return None  # only switched-off or missing fixes: nothing changed, no need to check

    document.save(check_path)
    if Path(check_path).read_bytes() == snapshot:
        return None  # the fixes found nothing to change: no need to check the file again
    after = run_verapdf(check_path, cancel_event)
    verdict = judge_fix(rule_id, stage, findings, after, snapshot, check_path)
    if not verdict.keep:
        document.restore(snapshot)
        report_warn(f"The fixes for rule {rule_id} were undone: {verdict.reason}.")
        return None
    if verdict.fixed or verdict.revealed:
        message = f"Rule {rule_id}: {verdict.fixed} problem(s) disappeared."
        if verdict.revealed:
            message += f" {verdict.revealed} other problem(s) appeared (often only revealed by this fix); they are handled in later steps."
        report_info(message)
    return after


def _batchable(stage: Stage, rule_id: str) -> bool:
    """Fixes that repair the whole document (they do not depend on where veraPDF points) and
    keep the page looking the same; font embedding has its own check and runs alone."""
    return (rule_id in stage.document_level and rule_id not in stage.shapes_may_change
            and rule_id not in stage.content_rules)


def _try_rules_together(
    document: WorkingDocument,
    stage: Stage,
    rule_ids: list[str],
    findings: list[VeraPdfViolation],
    check_path: str,
    cancel_event: Event | None,
) -> tuple[list[VeraPdfViolation] | None, str]:
    """
    Correct several whole-document rules and check the file once. Returns (new findings,
    "kept"), or (None, "unchanged") if the fixes changed nothing, or (None, "undone") after
    undoing all of them because the check failed; the caller then tries them one by one.
    """
    snapshot = document.snapshot()
    attempts = 0
    for rule_id in rule_ids:
        group = [f for f in findings if f.rule_id == rule_id]
        detected = map_violations(_select_for_correction(stage, rule_id, group), document.pdf, cancel_event)
        attempts += correct(detected, document.pdf, cancel_event)
    if attempts == 0:
        return None, "unchanged"
    document.save(check_path)
    if Path(check_path).read_bytes() == snapshot:
        return None, "unchanged"
    after = run_verapdf(check_path, cancel_event)
    reason = judge_together(rule_ids, stage, findings, after, snapshot, check_path)
    if reason is not None:
        document.restore(snapshot)
        report_debug(f"Rules {', '.join(rule_ids)} tried together were undone ({reason}); trying them one by one.")
        return None, "undone"
    before_counts, after_counts = _counts(findings), _counts(after)
    for rule_id in rule_ids:
        fixed = before_counts.get(rule_id, 0) - after_counts.get(rule_id, 0)
        if fixed:
            report_info(f"Rule {rule_id}: {fixed} problem(s) disappeared.")
    return after, "kept"


def _select_for_correction(stage: Stage, rule_id: str, group: list[VeraPdfViolation]) -> list[VeraPdfViolation]:
    """
    Document-level rules: one fix covers all findings, so only the first one is corrected.
    Page-level rules: one fix per page.
    """
    if rule_id in stage.document_level:
        return group[:1]
    if rule_id in stage.page_level:
        seen: set[int | None] = set()
        selected = []
        for finding in group:
            page = page_of_context(finding.context)
            if page not in seen:
                seen.add(page)
                selected.append(finding)
        return selected
    return group


def _counts(findings: list[VeraPdfViolation]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.rule_id] = counts.get(finding.rule_id, 0) + 1
    return counts


class _Progress:
    def __init__(self, callback: ProgressCallback | None) -> None:
        self._callback = callback

    def __call__(self, text: str, fraction: float) -> None:
        if self._callback is not None:
            self._callback(text, max(0.0, min(1.0, fraction)))


def _raise_if_cancelled(cancel_event: Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise InterruptedError("Pipeline cancelled")
