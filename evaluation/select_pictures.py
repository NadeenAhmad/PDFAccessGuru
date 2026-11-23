"""
Chooses the 40 pictures for the picture comparison and captures their exact AI input.

Pictures are drawn per FILE, not per picture: 40 files at random from the Kumar files whose pictures the tool
describes, then one picture at random from each (seed 20261111), never the same picture twice. Drawing per
picture would let two files with 186 small drawings each fill most of the sample.

    python evaluation/select_pictures.py          (plain python3; starts capture_pictures.py with the frozen Python)

Writes evaluation/work/pictures/selection.json and results/pictures/selection.csv (no picture content).
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import subprocess
from pathlib import Path

from paths import FROZEN_PYTHON, HERE, KUMAR, RESULTS, RUNS, WORK

SEED = 20261111
WANTED = 40
PICTURES = WORK / "pictures"


def files_with_pictures() -> list[str]:
    """Kumar files in which the tool described at least one picture (from the GPT-6 Luna run's reports)."""
    found = []
    for report in sorted((RUNS / "kumar" / "luna").glob("kumar-*/report.json")):
        if "." in report.parent.name:
            continue
        data = json.loads(report.read_text(encoding="utf-8"))
        if any(line.get("level") == "review" and line.get("image_png_base64") and "picture description" in line.get("message", "")
               for phase in data.get("phases", []) for correction in phase.get("corrections", []) or []
               for line in correction.get("lines", [])):
            found.append(report.parent.name)
    return found


def main() -> int:
    paths = {}
    with (RESULTS / "sets" / "kumar.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            paths.setdefault(row["run_id"], KUMAR / row["file"])
    candidates = files_with_pictures()
    generator = random.Random(SEED)
    generator.shuffle(candidates)
    chosen, seen_images = [], set()
    for run_id in candidates:
        if len(chosen) == WANTED:
            break
        folder = PICTURES / run_id
        if not (folder / "pictures.json").exists():
            subprocess.run([str(FROZEN_PYTHON), str(HERE / "capture_pictures.py"), str(paths[run_id]), str(folder)],
                           capture_output=True, timeout=7200)
        pictures = json.loads((folder / "pictures.json").read_text(encoding="utf-8")) if (folder / "pictures.json").exists() else []
        pictures = [p for p in pictures if hashlib.sha1((folder / f"{p['picture']}.png").read_bytes()).hexdigest() not in seen_images]
        if not pictures:
            continue
        picture = generator.choice(pictures)
        seen_images.add(hashlib.sha1((folder / f"{picture['picture']}.png").read_bytes()).hexdigest())
        chosen.append({"id": f"p{len(chosen) + 1:02d}", "file": run_id, "folder": str(folder), "picture": picture["picture"],
                       "page": picture["page"], "rules_source": picture.get("rules_source", "")})
        print(f"{chosen[-1]['id']}: {run_id}, page {picture['page']}", flush=True)
    (PICTURES / "selection.json").write_text(json.dumps(chosen, indent=1), encoding="utf-8")
    target = RESULTS / "pictures" / "selection.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "file", "picture", "page", "rules_source"])
        writer.writeheader()
        writer.writerows({key: row[key] for key in writer.fieldnames} for row in chosen)
    print(f"{len(chosen)} pictures chosen -> {target.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
