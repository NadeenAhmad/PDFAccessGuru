"""
Baseline: opendataloader-pdf 2.5.21 (Apache-2.0), its free automatic tagging ("tagged-pdf" output).
Its PDF/UA export is a paid edition and is not used. Each output is checked with check_one.py, the same
check PDFAccessGuru uses, and the original is checked too (the "before" value).

    python evaluation/baseline_odl.py SET [N]      (SET: kumar | safedocs | reference; N: only the first N files)

Outputs: evaluation/work/runs-opendataloader/SET/odl/RUN_ID/ ; table: results/opendataloader/SET__odl.csv
"""

from __future__ import annotations

import concurrent.futures
import csv
import json
import subprocess
import sys
import time

from paths import FROZEN_PYTHON, HERE, ODL_RUNS, ODL_TABLES, WORK
from run import files

ODL_PYTHON = WORK / "venv-odl" / "bin" / "python"
_CONVERT = ("import sys, opendataloader_pdf as o; "
            "o.convert(input_path=sys.argv[1], output_dir=sys.argv[2], format='tagged-pdf', quiet=True)")
_COLUMNS = ["run_id", "ok", "error", "seconds", "passes_before", "problems_before", "rules_before",
            "tagged_share_before", "passes", "problems", "rules", "tagged_share"]


def main(set_name: str, limit: int = 0, workers: int = 2) -> int:
    folder = ODL_RUNS / set_name / "odl"
    chosen = files(set_name)[: limit or None]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(lambda item: _convert(folder, *item), chosen))
    rows = []
    for run_id, path in chosen:
        target = folder / run_id
        result_file = target / "result.json"
        result = json.loads(result_file.read_text(encoding="utf-8"))
        before = _read(target / "check_before.json")
        after = _read(target / "check_after.json")
        rows.append({"run_id": run_id, "ok": result["ok"] and after.get("ok", False), "error": result.get("error", ""),
                     "seconds": result.get("seconds", ""),
                     "passes_before": before.get("passes", ""), "problems_before": before.get("problems", ""),
                     "rules_before": before.get("rules", ""), "tagged_share_before": before.get("tagged_share", ""),
                     "passes": after.get("passes", ""), "problems": after.get("problems", ""),
                     "rules": after.get("rules", ""), "tagged_share": after.get("tagged_share", "")})
    table = ODL_TABLES / f"{set_name}__odl.csv"
    table.parent.mkdir(parents=True, exist_ok=True)
    with table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"summary: {table.relative_to(HERE.parent)}")
    return 0


def _convert(folder, run_id, path) -> None:
    target = folder / run_id
    result_file = target / "result.json"
    if result_file.exists():
        return
    target.mkdir(parents=True, exist_ok=True)
    result = {"run_id": run_id, "ok": False, "error": ""}
    started = time.perf_counter()
    try:
        done = subprocess.run([str(ODL_PYTHON), "-I", "-c", _CONVERT, str(path), str(target)],
                              capture_output=True, text=True, timeout=3600)
        result["seconds"] = round(time.perf_counter() - started, 1)
        outputs = [p for p in target.glob("*.pdf")]
        if not outputs:
            result["error"] = ("no tagged PDF written: " + (done.stderr or done.stdout)[-300:]).strip()
        else:
            subprocess.run([str(FROZEN_PYTHON), "-I", str(HERE / "check_one.py"), str(outputs[0]),
                            str(target / "check_after.json")], timeout=3600)
            result["ok"] = True
    except subprocess.TimeoutExpired:
        result["error"] = "timeout after 3600 s"
    subprocess.run([str(FROZEN_PYTHON), "-I", str(HERE / "check_one.py"), str(path),
                    str(target / "check_before.json")], timeout=3600)
    result_file.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"{time.strftime('%H:%M:%S')} {run_id}: {'ok' if result['ok'] else result['error'][:100]}", flush=True)


def _read(path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 0))
