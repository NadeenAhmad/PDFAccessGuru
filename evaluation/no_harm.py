"""
"Do no harm": compares every fixed PDF with its original, independently of the tool's own safeguards.

- text: the text of each page (PyMuPDF, spaces normalised) must stay the same;
- looks: each page is drawn small (40 dpi, grey) and compared; a page counts as changed when more than
  0.5 % of its pixels differ by more than 10 % (anti-aliasing and font smoothing stay below that).

    python evaluation/no_harm.py SET SETTING [--workers N]      (plain python3; uses the frozen Python per file)

Writes noharm.json next to each fixed PDF and results/runs/SET__SETTING__noharm.csv.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import subprocess
import sys
from pathlib import Path

from paths import FROZEN_PYTHON, HERE, RESULTS, RUN_TABLES, RUNS
from run import files

_COMPARE = r'''
import json, re, sys
import pymupdf
original, fixed, target = sys.argv[1:4]
def words(page):
    return re.sub(r"\s+", " ", page.get_text()).strip()
result = {"pages": 0, "text_changed_pages": [], "look_changed_pages": [], "error": ""}
try:
    with pymupdf.open(original) as a, pymupdf.open(fixed) as b:
        result["pages"] = len(a)
        if len(a) != len(b):
            result["error"] = f"page count {len(a)} -> {len(b)}"
        for number in range(min(len(a), len(b))):
            if words(a[number]) != words(b[number]):
                result["text_changed_pages"].append(number + 1)
            pa = a[number].get_pixmap(dpi=40, colorspace=pymupdf.csGRAY, alpha=False)
            pb = b[number].get_pixmap(dpi=40, colorspace=pymupdf.csGRAY, alpha=False)
            if (pa.width, pa.height) != (pb.width, pb.height):
                result["look_changed_pages"].append(number + 1); continue
            sa, sb = pa.samples, pb.samples
            different = sum(1 for x, y in zip(sa, sb) if abs(x - y) > 25)
            if different > 0.005 * len(sa):
                result["look_changed_pages"].append(number + 1)
except Exception as error:
    result["error"] = f"{type(error).__name__}: {error}"[:300]
open(target, "w").write(json.dumps(result))
'''


def check(original: Path, folder: Path) -> dict:
    target = folder / "noharm.json"
    fixed = folder / "fixed.pdf"
    if not fixed.exists():
        return {"run_id": folder.name, "checked": False}
    if not target.exists():
        subprocess.run([str(FROZEN_PYTHON), "-I", "-c", _COMPARE, str(original), str(fixed), str(target)], timeout=7200)
    result = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {"error": "no result"}
    text_pages = result.get("text_changed_pages", [])
    look_pages = result.get("look_changed_pages", [])
    changed = " ".join(str(number) for number in sorted(set(text_pages) | set(look_pages)))
    return {"run_id": folder.name, "checked": True, "pages": result.get("pages", ""),
            "text_changed_pages": len(text_pages), "look_changed_pages": len(look_pages),
            "changed_page_numbers": changed[:200], "error": result.get("error", "")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("set")
    parser.add_argument("setting")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    folder = RUNS / args.set / args.setting
    jobs = [(path, folder / run_id) for run_id, path in files(args.set) if (folder / run_id / "fixed.pdf").exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda job: check(*job), jobs))
    table = RUN_TABLES / f"{args.set}__{args.setting}__noharm.csv"
    with table.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["run_id", "checked", "pages", "text_changed_pages",
                                                    "look_changed_pages", "changed_page_numbers", "error"])
        writer.writeheader()
        writer.writerows(rows)
    changed = sum(1 for row in rows if row.get("text_changed_pages") or row.get("look_changed_pages"))
    print(f"{args.set}/{args.setting}: {len(rows)} files checked, {changed} with a changed page -> {table.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
