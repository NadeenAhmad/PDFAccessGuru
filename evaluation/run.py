"""
Runs the frozen PDFAccessGuru version (1.1.0) on a test set with one AI setting, file by file.

    python evaluation/run.py SET SETTING [--limit N] [--timeout SECONDS]
        SET:      kumar | safedocs | reference
        SETTING:  rules (no AI) | local (Gemma 4 on this computer) | luna (GPT-6 Luna online, costs money)

Raw outputs go to evaluation/work/runs/SET/SETTING/RUN_ID/ (fixed.pdf, report.json, result.json).
A finished file is not run again, so a stopped run can simply be started again.
Online runs: the budget is checked before every file, and every request's price is logged (budget.py).
At the end, results/runs/SET__SETTING.csv is rebuilt from all result.json files.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

import budget
from paths import FROZEN_PYTHON, HERE, KUMAR, REFERENCE_SUITE, RESULTS, RUN_TABLES, RUNS, SAFEDOCS

ONLINE = {"luna", "gemma"}
_COLUMNS = ["run_id", "setting", "ok", "error", "seconds", "passes", "problems_before", "problems_after",
            "problems_fixed", "rules_before", "rules_after", "review_items", "tagged_share_before",
            "tagged_share_after", "contrast_low", "ai_text", "ai_picture", "paid_requests", "cost_usd"]


def files(set_name: str) -> list[tuple[str, Path]]:
    """(run_id, path) for every distinct file of the set, in the order of the set list."""
    base = {"kumar": KUMAR, "safedocs": SAFEDOCS, "reference": REFERENCE_SUITE}[set_name]
    with (RESULTS / "sets" / f"{set_name}.csv").open(encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["run_id"]]
    seen, chosen = set(), []
    for row in rows:
        if row["run_id"] not in seen:
            seen.add(row["run_id"])
            chosen.append((row["run_id"], base / row["file"]))
    return chosen


def summarize(set_name: str, setting: str) -> Path:
    folder = RUNS / set_name / setting
    rows = []
    for result_file in sorted(folder.glob("*/result.json")):
        if "." in result_file.parent.name:               # first attempts and interrupted runs are kept, not counted
            continue
        result = json.loads(result_file.read_text(encoding="utf-8"))
        requests = result.get("ai_requests") or {}
        row = {column: result.get(column, "") for column in _COLUMNS}
        row.update(run_id=result_file.parent.name, ai_text=requests.get("text", 0), ai_picture=requests.get("picture", 0),
                   paid_requests=len(result.get("paid_requests", [])), cost_usd=result.get("cost_usd", 0.0))
        rows.append(row)
    target = RUN_TABLES / f"{set_name}__{setting}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("set", choices=["kumar", "safedocs", "reference"])
    parser.add_argument("setting", choices=["rules", "local", "luna", "gemma"])
    parser.add_argument("--limit", type=int, default=0, help="only the first N files (trial runs)")
    parser.add_argument("--sample", type=int, default=0, help="a fixed random sample of N files (seed 20261111)")
    parser.add_argument("--workers", type=int, default=1, help="files run at the same time")
    parser.add_argument("--timeout", type=int, default=0,
                        help="seconds per file before it counts as failed (default: 3600 online, 7200 on this computer)")
    parser.add_argument("--retry-failed", action="store_true", help="run files that failed before once more")
    parser.add_argument("--only", nargs="*", default=[], help="only these run ids")
    parser.add_argument("--forecast", type=float, default=0.05, help="USD one file may cost at most (online runs)")
    args = parser.parse_args()

    args.timeout = args.timeout or (3600 if args.setting in ONLINE else 7200)
    chosen = [item for item in files(args.set) if not args.only or item[0] in args.only][: args.limit or None]
    if args.sample:
        keep = set(random.Random(20261111).sample([run_id for run_id, _ in chosen], args.sample))
        chosen = [item for item in chosen if item[0] in keep]
    folder = RUNS / args.set / args.setting
    log = folder / "run.log"
    folder.mkdir(parents=True, exist_ok=True)
    lock = threading.Lock()
    stop = threading.Event()

    def say(text: str) -> None:
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {text}"
        with lock:
            print(line, flush=True)
            with log.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def account(target: Path, result: dict, run_id: str) -> None:
        paid_log = target / "paid.jsonl"
        if paid_log.exists():                             # also the requests of a run that was stopped
            result["paid_requests"] = [json.loads(line) for line in paid_log.read_text(encoding="utf-8").splitlines() if line]
        if args.setting in ONLINE:
            requests = [request for request in result.get("paid_requests", []) if request.get("id")]
            with lock:
                result["cost_usd"] = round(budget.record(f"{args.set}/{args.setting}/{run_id}", requests), 6)
                unknown = len(result.get("paid_requests", [])) - len(requests)
                if unknown:                               # a request without an id (e.g. an error answer): count it safely
                    budget.note(f"{args.set}/{args.setting}/{run_id}", 0.01 * unknown,
                                f"{unknown} request(s) without id, counted as USD 0.01 each")
                    result["cost_usd"] += 0.01 * unknown

    # A file that was stopped half-way (e.g. the runs were restarted): log what it paid, then run it again.
    for target in folder.glob("*"):
        if target.is_dir() and "." not in target.name and not (target / "result.json").exists():
            partial = {"paid_requests": []}
            account(target, partial, target.name + " (interrupted)")
            target.rename(target.with_name(f"{target.name}.interrupted-{time.strftime('%H%M%S')}"))
            say(f"{target.name}: interrupted earlier, paid requests logged, runs again")

    def one(number: int, run_id: str, path: Path) -> None:
        if stop.is_set():
            return
        target = folder / run_id
        if (target / "result.json").exists():
            previous = json.loads((target / "result.json").read_text(encoding="utf-8"))
            if previous.get("ok") or not args.retry_failed or previous.get("retried"):
                return
            say(f"[{number}/{len(chosen)}] {run_id}: trying once more (first attempt: {previous.get('error', '')[:100]})")
            target.rename(target.with_name(run_id + ".attempt1"))
        if args.setting in ONLINE:
            try:
                with lock:
                    budget.check(args.forecast * args.workers)
            except budget.BudgetExceeded as reason:
                say(f"STOPPED before {run_id}: {reason}")
                stop.set()
                return
        started = time.time()
        try:
            subprocess.run([str(FROZEN_PYTHON), "-I", str(HERE / "fix_one.py"), str(path), str(target), args.setting],
                           timeout=args.timeout, capture_output=True, check=False)
        except subprocess.TimeoutExpired:
            target.mkdir(parents=True, exist_ok=True)
            (target / "result.json").write_text(json.dumps({"setting": args.setting, "ok": False, "error": f"timeout after {args.timeout} s",
                                                            "seconds": args.timeout, "paid_requests": []}), encoding="utf-8")
        result_file = target / "result.json"
        result = json.loads(result_file.read_text(encoding="utf-8")) if result_file.exists() else \
            {"setting": args.setting, "ok": False, "error": "no result written", "paid_requests": []}
        account(target, result, run_id)
        result["retried"] = target.with_name(run_id + ".attempt1").exists()
        result["wall_seconds"] = round(time.time() - started, 1)     # differs from "seconds" if the Mac slept meanwhile
        target.mkdir(parents=True, exist_ok=True)
        result_file.write_text(json.dumps(result, indent=1), encoding="utf-8")
        status = "ok" if result.get("ok") else f"FAILED ({result.get('error', '')[:120]})"
        extra = f", USD {result.get('cost_usd', 0):.4f}; {budget.status()}" if args.setting in ONLINE else ""
        say(f"[{number}/{len(chosen)}] {run_id}: {status}, {time.time() - started:.0f} s{extra}")

    say(f"start: {args.set} / {args.setting}, {len(chosen)} files, {args.workers} at a time")
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in [pool.submit(one, number, run_id, path) for number, (run_id, path) in enumerate(chosen, start=1)]:
            future.result()
    say(f"summary: {summarize(args.set, args.setting).relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
