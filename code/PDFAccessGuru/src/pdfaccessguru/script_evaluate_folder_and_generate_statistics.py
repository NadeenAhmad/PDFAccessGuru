"""
Collect pipeline statistics for every PDF under a folder tree.

Each PDF is processed by a separate child process so a run that exceeds the
configured timeout can be aborted without affecting the remaining files.
A thread pool in the parent starts up to ``--jobs`` of those children at once;
the threads only wait on subprocesses and never run the pipeline in-process.
``--jobs 1`` (the default) is sequential. Values greater than 1 share veraPDF
and OpenRouter capacity, so memory, CPU, and API rate limits still apply.

Usage:
    python src/pdfaccessguru/evaluate_pdf_folder.py <pdf_folder> [--timeout SECONDS] [--jobs N]

    --timeout defaults to 300 seconds (5 minutes) when omitted.
    --jobs defaults to 1 (one pipeline child at a time).

Examples:
    python src/pdfaccessguru/script_evaluate_folder_and_generate_statistics.py src/test/resources/validation_Set
    python src/pdfaccessguru/script_evaluate_folder_and_generate_statistics.py src/test/resources/validation_Set --timeout 3600
    python src/pdfaccessguru/script_evaluate_folder_and_generate_statistics.py src/test/resources/ProfPDFs --jobs 4
    python src/pdfaccessguru/script_evaluate_folder_and_generate_statistics.py src/test/resources/ProfPDFs --timeout 3600 --jobs 4

Outputs (written under pdf_cache/ at the repository root):
    <relative_path>_output.pdf   - corrected PDF produced by the pipeline
    <relative_path>_pipeline.log - stdout/stderr of the child process
    <relative_path>_result.json  - temporary per-PDF violation counts
    pipeline_statistics.json     - global, per-violation, and per-PDF stats
"""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
from typing import Any

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

REPO_ROOT = Path(__file__).resolve().parents[2]
PDF_CACHE_DIR = REPO_ROOT / "pdf_cache"
STATISTICS_PATH = PDF_CACHE_DIR / "pipeline_statistics.json"
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_JOBS = 1
HEARTBEAT_INTERVAL_SECONDS = 5.0
IS_WINDOWS = os.name == "nt"


def _phase_summary(report: dict[str, Any], phase_name: str) -> dict[str, Any]:
    """
    Return the summary dict for a named phase from a pipeline report.

    Arguments:
        report: Serialized pipeline report returned by ``run_pipeline``.
        phase_name: Phase to look up, e.g. ``"detection"`` or ``"verification"``.

    Returns:
        The phase summary dictionary, or an empty dict when the phase is missing.
    """
    for phase in report.get("phases", []):
        if phase.get("name") == phase_name:
            return phase.get("summary") or {}
    return {}


def _run_worker(pdf_path: Path, output_path: Path, result_path: Path) -> int:
    """
    Run the full pipeline on one PDF and write violation counts to ``result_path``.

    Invoked by the parent process via ``--worker``. Tracebacks are printed so
    they land in the redirected pipeline log file.

    Arguments:
        pdf_path: Input PDF to process.
        output_path: Destination for the corrected PDF.
        result_path: JSON file that receives the before/after totals and
            per-name violation counts.

    Returns:
        ``0`` on success, ``1`` when the pipeline raises an exception.
    """
    from pdfaccessguru.pipeline.pipeline import run_pipeline

    try:
        report = run_pipeline(str(pdf_path), str(output_path))
    except Exception:
        traceback.print_exc()
        return 1

    detection = _phase_summary(report, "detection")
    verification = _phase_summary(report, "verification")
    result = {
        "violations_before_correction": detection.get("total_detected_violations"),
        "violations_after_correction": verification.get("total_detected_violations"),
        "violations_by_name_before": detection.get("violations_by_name") or {},
        "violations_by_name_after": verification.get("violations_by_name") or {},
    }
    result_path.write_text(json.dumps(result), encoding="utf-8")
    return 0


def _spawn_kwargs() -> dict[str, Any]:
    """
    Return ``Popen`` kwargs that isolate the child in its own process group.

    Isolation is required so a timeout can kill the child together with
    grandchildren such as the veraPDF CLI.
    """
    if IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def _kill_process_tree(process: subprocess.Popen[Any]) -> None:
    """
    Terminate ``process`` and every process it spawned.

    On Windows this uses ``taskkill /T``. On POSIX it sends ``SIGKILL`` to the
    child's process group. Falls back to ``process.kill()`` when the group is
    already gone.
    """
    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            process.kill()

    try:
        process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.kill()


def _artifact_stem(relative_key: str) -> str:
    """
    Flatten a relative PDF path into a file-name stem for ``pdf_cache/``.

    Path separators and other unsafe characters are replaced with ``_`` so
    nested PDFs with identical file names do not overwrite each other's
    artifacts.
    """
    stem = relative_key[: -len(".pdf")] if relative_key.endswith(".pdf") else relative_key
    return "".join(
        character if character.isalnum() or character in "._-" else "_"
        for character in stem
    )


def _process_pdf(
    pdf_path: Path,
    artifact_stem: str,
    timeout_seconds: float,
) -> tuple[dict[str, Any], str]:
    """
    Run the pipeline on one PDF in a child process and return its statistics.

    Does not print. Callers that need console progress should use
    ``_process_pdf_with_progress``.

    Arguments:
        pdf_path: Absolute path of the PDF to process.
        artifact_stem: Flat stem used for files written under ``pdf_cache/``.
        timeout_seconds: Wall-clock limit after which the child is aborted.

    Returns:
        A pair ``(entry, status)`` where ``entry`` holds duration, totals, and
        per-name counts, and ``status`` is ``"ok"``, ``"timeout"``, or ``"failed"``.
    """
    output_path = PDF_CACHE_DIR / f"{artifact_stem}_output.pdf"
    result_path = PDF_CACHE_DIR / f"{artifact_stem}_result.json"
    log_path = PDF_CACHE_DIR / f"{artifact_stem}_pipeline.log"
    result_path.unlink(missing_ok=True)

    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        str(pdf_path),
        str(output_path),
        str(result_path),
    ]

    start = time.perf_counter()
    with log_path.open("w", encoding="utf-8", errors="replace") as log_file:
        process = subprocess.Popen(
            command,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            **_spawn_kwargs(),
        )
        try:
            exit_code = process.wait(timeout=timeout_seconds)
            status = "ok" if exit_code == 0 else "failed"
        except subprocess.TimeoutExpired:
            _kill_process_tree(process)
            status = "timeout"
    duration_seconds = round(time.perf_counter() - start, 2)

    counts: dict[str, Any] = {
        "violations_before_correction": None,
        "violations_after_correction": None,
        "violations_by_name_before": {},
        "violations_by_name_after": {},
    }
    if status == "ok" and result_path.exists():
        counts.update(json.loads(result_path.read_text(encoding="utf-8")))
    elif status == "ok":
        status = "failed"

    return {"total_duration_seconds": duration_seconds, **counts}, status


def _format_run_summary(entry: dict[str, Any], status: str) -> str:
    """Build the one-line console summary printed after each PDF run."""
    duration = entry["total_duration_seconds"]
    before = entry["violations_before_correction"]
    after = entry["violations_after_correction"]
    if before is None or after is None:
        return f"  {status} after {duration}s"

    corrected = before - after
    return (
        f"  {status} after {duration}s "
        f"(before={before}, corrected={corrected}, remaining={after})"
    )


def _correction_rate(corrected: int, before: int) -> float:
    """Return ``corrected / before``, or ``0.0`` when ``before`` is not positive."""
    if before <= 0:
        return 0.0
    return round(corrected / before, 4)


def _count_summary(before: int, after: int) -> dict[str, Any]:
    """Build the shared before/after/corrected/rate object for global or per-violation stats."""
    corrected = before - after
    return {
        "violations_before_correction": before,
        "violations_after_correction": after,
        "corrected": corrected,
        "correction_rate": _correction_rate(corrected, before),
    }


def _violations_from_counts(
    before_by_name: dict[str, int],
    after_by_name: dict[str, int],
) -> list[dict[str, Any]]:
    """
    Build sorted per-violation summaries from before/after name counts.

    Rows are sorted by lowest correction rate first, then highest remaining
    count, then name.
    """
    violations = []
    for name in set(before_by_name) | set(after_by_name):
        summary = _count_summary(
            int(before_by_name.get(name, 0)),
            int(after_by_name.get(name, 0)),
        )
        violations.append({"name": name, **summary})

    violations.sort(
        key=lambda row: (
            row["correction_rate"],
            -row["violations_after_correction"],
            row["name"],
        )
    )
    return violations


def _build_final_statistics(pdf_entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Aggregate per-PDF entries into global, per-violation, and per-PDF statistics.

    Successful PDFs (numeric before/after totals) contribute to ``global`` and
    ``violations``. Failed and timeout entries stay in ``pdfs`` with ``null``
    counts, an empty ``violations`` list, and are ignored for rates. Each PDF
    also gets its own ``violations`` rows in the same shape and sort order as
    the global list.

    Arguments:
        pdf_entries: Ordered map of relative PDF path to a statistics entry.

    Returns:
        The wrapped statistics dict written to ``pipeline_statistics.json``.
    """
    pdfs: dict[str, dict[str, Any]] = {}
    before_by_name: dict[str, int] = defaultdict(int)
    after_by_name: dict[str, int] = defaultdict(int)
    total_before = 0
    total_after = 0

    for relative_key, entry in pdf_entries.items():
        before = entry["violations_before_correction"]
        after = entry["violations_after_correction"]
        pdf_before_by_name = entry.get("violations_by_name_before") or {}
        pdf_after_by_name = entry.get("violations_by_name_after") or {}

        pdf_violations: list[dict[str, Any]] = []
        if before is not None and after is not None:
            pdf_violations = _violations_from_counts(pdf_before_by_name, pdf_after_by_name)
            total_before += int(before)
            total_after += int(after)
            for name, count in pdf_before_by_name.items():
                before_by_name[name] += int(count)
            for name, count in pdf_after_by_name.items():
                after_by_name[name] += int(count)

        pdfs[relative_key] = {
            "total_duration_seconds": entry["total_duration_seconds"],
            "violations_before_correction": before,
            "violations_after_correction": after,
            "violations": pdf_violations,
        }

    return {
        "global": _count_summary(total_before, total_after),
        "violations": _violations_from_counts(before_by_name, after_by_name),
        "pdfs": pdfs,
    }


def _heartbeat_loop(
    active_workers: dict[int, tuple[str, float]],
    print_lock: threading.Lock,
    stop_heartbeat: threading.Event,
    total: int,
    max_workers: int,
) -> None:
    """
    Print the PDFs still running every ``HEARTBEAT_INTERVAL_SECONDS``.

    Skips a cycle when no workers are registered. Stops as soon as
    ``stop_heartbeat`` is set.

    Arguments:
        active_workers: Shared map of 1-based index to ``(relative_key, start)``.
        print_lock: Lock that serializes console output with worker threads.
        stop_heartbeat: Event that ends the loop after all jobs finish.
        total: Number of PDFs in the folder tree.
        max_workers: Size of the thread pool (``--jobs``).
    """
    while not stop_heartbeat.wait(timeout=HEARTBEAT_INTERVAL_SECONDS):
        now = time.perf_counter()
        with print_lock:
            snapshot = sorted(active_workers.items())
            if not snapshot:
                continue
            print(f"still running ({len(snapshot)}/{max_workers} workers):")
            for index, (relative_key, start) in snapshot:
                elapsed = int(now - start)
                print(f"  [{index}/{total}] {relative_key}  {elapsed}s")
            sys.stdout.flush()


def _process_pdf_with_progress(
    index: int,
    total: int,
    folder: Path,
    pdf_path: Path,
    timeout_seconds: float,
    print_lock: threading.Lock,
    active_workers: dict[int, tuple[str, float]],
) -> tuple[str, dict[str, Any]]:
    """
    Run one PDF child and print thread-safe start and completion lines.

    The start line is printed when this worker thread begins, not when the
    future is submitted, so ``index`` matches a job that is actually running.
    The job is registered in ``active_workers`` until it finishes so the
    heartbeat can list it.

    Arguments:
        index: 1-based position of this PDF in the sorted scan order.
        total: Number of PDFs in the folder tree.
        folder: Root directory used to compute the relative cache key.
        pdf_path: Absolute path of the PDF to process.
        timeout_seconds: Wall-clock limit passed through to ``_process_pdf``.
        print_lock: Lock that serializes console output across worker threads.
        active_workers: Shared map of in-flight jobs for the heartbeat printer.

    Returns:
        A pair ``(relative_key, entry)`` for the aggregated statistics dict.
    """
    relative_key = pdf_path.relative_to(folder).as_posix()
    try:
        with print_lock:
            active_workers[index] = (relative_key, time.perf_counter())
            print(f"[{index}/{total}] started {relative_key}", flush=True)

        entry, status = _process_pdf(
            pdf_path,
            _artifact_stem(relative_key),
            timeout_seconds,
        )

        with print_lock:
            active_workers.pop(index, None)
            print(
                f"[{index}/{total}] {relative_key}{_format_run_summary(entry, status)}",
                flush=True,
            )
        return relative_key, entry
    finally:
        with print_lock:
            active_workers.pop(index, None)


def _run_statistics(folder: Path, timeout_seconds: float, jobs: int) -> None:
    """
    Scan ``folder`` recursively, process every PDF, and write the statistics JSON.

    Up to ``jobs`` child pipeline processes run at once. A thread pool in this
    parent only waits on those children; it does not import or execute the
    pipeline in-process. A heartbeat thread prints the still-running PDFs and
    their elapsed times every ``HEARTBEAT_INTERVAL_SECONDS``. Cache artifacts
    stay unique per flattened relative path. ``pipeline_statistics.json`` is
    written once after every job finishes, with global and per-violation
    correction rates plus per-PDF entries (including per-violation stats)
    in sorted scan order.

    Arguments:
        folder: Root directory that is searched for ``*.pdf`` files.
        timeout_seconds: Per-PDF wall-clock timeout in seconds.
        jobs: Maximum number of pipeline child processes to run in parallel.

    Raises:
        NotADirectoryError: If ``folder`` does not exist or is not a directory.
        FileNotFoundError: If no PDF files are found under ``folder``.
    """
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a directory: {folder}")

    pdf_files = sorted(folder.rglob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {folder}")

    PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    total = len(pdf_files)
    print_lock = threading.Lock()
    active_workers: dict[int, tuple[str, float]] = {}
    stop_heartbeat = threading.Event()
    completed: dict[str, dict[str, Any]] = {}

    heartbeat = threading.Thread(
        target=_heartbeat_loop,
        args=(active_workers, print_lock, stop_heartbeat, total, jobs),
        daemon=True,
        name="evaluate-pdf-heartbeat",
    )

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = [
            executor.submit(
                _process_pdf_with_progress,
                index,
                total,
                folder,
                pdf_path,
                timeout_seconds,
                print_lock,
                active_workers,
            )
            for index, pdf_path in enumerate(pdf_files, start=1)
        ]
        heartbeat.start()
        try:
            for future in as_completed(futures):
                relative_key, entry = future.result()
                completed[relative_key] = entry
        finally:
            stop_heartbeat.set()

    ordered_keys = [pdf_path.relative_to(folder).as_posix() for pdf_path in pdf_files]
    statistics = _build_final_statistics({key: completed[key] for key in ordered_keys})

    STATISTICS_PATH.write_text(json.dumps(statistics, indent=2), encoding="utf-8")
    global_rate = statistics["global"]["correction_rate"]
    print(f"Wrote statistics to {STATISTICS_PATH} (global correction rate: {global_rate})")


def main() -> None:
    """Parse CLI arguments and either run as a worker or collect statistics."""
    parser = argparse.ArgumentParser(
        description=(
            "Run the PDFAccessGuru pipeline on every PDF in a folder tree "
            "and collect statistics."
        ),
    )
    parser.add_argument(
        "folder",
        nargs="?",
        type=Path,
        help="Folder that is scanned recursively for PDF files.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=(
            "Seconds after which a pipeline run is aborted and counted as failed "
            f"(default: {DEFAULT_TIMEOUT_SECONDS:g})."
        ),
    )
    parser.add_argument(
        "--jobs",
        "-j",
        type=int,
        default=DEFAULT_JOBS,
        help=(
            "Maximum number of pipeline child processes to run in parallel "
            f"(default: {DEFAULT_JOBS})."
        ),
    )
    parser.add_argument(
        "--worker",
        nargs=3,
        metavar=("PDF_PATH", "OUTPUT_PATH", "RESULT_PATH"),
        help=argparse.SUPPRESS,
    )
    arguments = parser.parse_args()

    if arguments.worker is not None:
        pdf_path, output_path, result_path = (Path(value) for value in arguments.worker)
        sys.exit(_run_worker(pdf_path, output_path, result_path))

    if arguments.folder is None:
        parser.error("the following arguments are required: folder")
    if arguments.timeout <= 0:
        parser.error("--timeout must be greater than 0")
    if arguments.jobs < 1:
        parser.error("--jobs must be greater than or equal to 1")

    _run_statistics(arguments.folder, arguments.timeout, arguments.jobs)


if __name__ == "__main__":
    main()
