"""
Scores of the PAVE-style check: per tool and criterion, correct / (correct + wrong or missing), summed over the
documents, for each judge and their mean; "pages" criteria count correct pages. Like PAVE 2.0's Table 1, the
overall score is the mean over the criteria that occur in the documents.

    python3 evaluation/score_pave.py JUDGE1.csv [JUDGE2.csv ...]

Reads evaluation/work/pave/key.json (version code -> document and tool). Writes results/pave/scores.csv
(tool, criterion, per-judge score, mean) and prints a table.
"""

from __future__ import annotations

import collections
import csv
import json
import sys
from pathlib import Path

from build_pave_sheet import CRITERIA, PAVE
from paths import RESULTS


def judge_scores(answers: Path, key: dict) -> dict[tuple[str, str], tuple[int, int]]:
    """(tool, criterion) -> (correct, wrong or missing) for one judge."""
    values: dict[str, str] = {}
    with answers.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            values[f"{row['code']}-{row['field']}"] = row["value"]
    with (RESULTS / "pave" / "selection.csv").open(encoding="utf-8") as handle:
        pages_used = {row["doc"]: int(row["pages_used"]) for row in csv.DictReader(handle)}
    totals: dict[tuple[str, str], list[int]] = collections.defaultdict(lambda: [0, 0])
    for code, info in key.items():
        for criterion, _, _, kind in CRITERIA:
            field = f"{code}-{criterion}"
            if kind == "pages":
                pages = pages_used[info["doc"]]
                correct = sum(1 for n in range(1, pages + 1) if values.get(f"{field}-p{n}") == "yes")
                totals[(info["tool"], criterion)][0] += correct
                totals[(info["tool"], criterion)][1] += pages - correct
            elif values.get(f"{field}-none") != "yes":
                totals[(info["tool"], criterion)][0] += int(values.get(f"{field}-ok") or 0)
                totals[(info["tool"], criterion)][1] += int(values.get(f"{field}-bad") or 0)
    return {k: (v[0], v[1]) for k, v in totals.items()}


def main(files: list[Path]) -> int:
    key = json.loads((PAVE / "key.json").read_text(encoding="utf-8"))
    judges = [judge_scores(path, key) for path in files]
    tools = sorted({info["tool"] for info in key.values()})
    rows = []
    for tool in tools:
        overall = []
        for criterion, name, _, _ in CRITERIA:
            scores = []
            for judge in judges:
                correct, wrong = judge.get((tool, criterion), (0, 0))
                scores.append(None if correct + wrong == 0 else 100 * correct / (correct + wrong))
            present = [s for s in scores if s is not None]
            mean = sum(present) / len(present) if present else None
            if mean is not None:
                overall.append(mean)
            rows.append({"tool": tool, "criterion": name, **{f"judge_{n + 1}": "" if s is None else f"{s:.1f}"
                                                            for n, s in enumerate(scores)},
                         "mean": "" if mean is None else f"{mean:.1f}"})
        rows.append({"tool": tool, "criterion": "Average", "mean": f"{sum(overall) / len(overall):.1f}" if overall else ""})
    target = RESULTS / "pave" / "scores.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    fields = ["tool", "criterion"] + [f"judge_{n + 1}" for n in range(len(judges))] + ["mean"]
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(f"{row['tool']:<24} {row['criterion']:<22} {row['mean']:>6}")
    print(f"-> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main([Path(arg) for arg in sys.argv[1:]]))
