"""
The Acrobat Pro baseline: which files Acrobat gets, and the check of what it gives back.

Acrobat Pro cannot be scripted from outside, so its part is done by hand with one saved guided action
("PDFAccessGuruEval": Autotag document, then Set Tab Order Property) run on the whole input folder.
Acrobat writes each result next to the input as NAMEAdobeFix.pdf; move them to work/acrobat/output/.

    python evaluation/acrobat_files.py prepare     # copies the untagged Kumar and SafeDocs files (and the 4 PAVE
                                                   # documents) to work/acrobat/input/, named by run_id
    (run the guided action in Acrobat Pro on work/acrobat/input/, move the results to work/acrobat/output/)
    python evaluation/acrobat_files.py check       # checks every Acrobat output exactly like the other tools' outputs
    python evaluation/acrobat_summary.py           # the comparison table

Only files that are untagged before are given to Acrobat: on tagged files Autotag replaces the author's tags.
The check (check_one.py, run with the frozen Python) writes work/runs-acrobat/SET/RUN_ID/check.json.
"""

from __future__ import annotations

import csv
import shutil
import subprocess
import sys

from paths import FROZEN_PYTHON, HERE, KUMAR, RESULTS, SAFEDOCS, WORK

INPUT = WORK / "acrobat" / "input"
OUTPUT = WORK / "acrobat" / "output"
CHECKS = WORK / "runs-acrobat"


def untagged(set_name: str, base) -> list[tuple[str, object]]:
    with (RESULTS / "sets" / f"{set_name}.csv").open(encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["run_id"] and row["tagged"] == "False"]
    chosen = {}
    for row in rows:
        chosen.setdefault(row["run_id"], base / row["file"])
    return list(chosen.items())


def prepare() -> int:
    INPUT.mkdir(parents=True, exist_ok=True)
    files = untagged("kumar", KUMAR) + untagged("safedocs", SAFEDOCS)
    files += [(path.stem, path) for path in sorted((WORK / "pave" / "input").glob("pave-*.pdf"))]
    for run_id, source in files:
        shutil.copyfile(source, INPUT / f"{run_id}.pdf")
    print(f"{len(files)} files in {INPUT}")                      # paper: 20 Kumar + 136 SafeDocs + 4 PAVE = 160
    return 0


def check() -> int:
    outputs = sorted(OUTPUT.glob("*AdobeFix.pdf"))
    for output in outputs:
        run_id = output.name[: -len("AdobeFix.pdf")]
        target = CHECKS / run_id.split("-")[0] / run_id / "check.json"
        if target.exists():
            continue
        subprocess.run([str(FROZEN_PYTHON), str(HERE / "check_one.py"), str(output), str(target)], check=False)
        print(run_id, "checked")
    print(f"{len(outputs)} Acrobat outputs, checks in {CHECKS}")
    return 0


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command not in ("prepare", "check"):
        sys.exit(__doc__)
    sys.exit(prepare() if command == "prepare" else check())
