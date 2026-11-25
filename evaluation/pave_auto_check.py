"""
The 4 documents of the PAVE comparison: the automatic check of every tool's output, the same check as for all other
outputs (check_one.py: veraPDF PDF/UA-1 and the share of text a screen reader reaches). How well the documents are
tagged is judged by people (build_pave_sheet.py, score_expert.py); this is only the automatic part.

Outputs of each tool: work/pave/outputs/TOOL/pave-N.pdf (PDFAccessGuru by run_all.sh; Acrobat via acrobat_files.py;
opendataloader-pdf by baseline_odl.py on these files; PAVE 2.0 by hand on pave-pdf.org with all its automatic buttons).

    python evaluation/pave_auto_check.py

Writes results/pave/auto-checks/TOOL/pave-N.json (kept, not checked again) and results/pave/auto-check.md.
"""

from __future__ import annotations

import collections
import csv
import json
import subprocess

from paths import FROZEN_PYTHON, HERE, RESULTS, WORK

TOOLS = {"pdfaccessguru-1.1.0": "PDFAccessGuru 1.1.0 (Gemma 4 26B)", "pave": "PAVE 2.0 (all automatic buttons, by hand)",
         "acrobat": "Acrobat Pro (Autotag)", "odl": "opendataloader-pdf"}
CHECKS = RESULTS / "pave" / "auto-checks"


def share(result: dict) -> str:
    return "–" if result.get("tagged_share") is None else f"{result['tagged_share']:.0%}"


def main() -> int:
    with (RESULTS / "pave" / "selection.csv").open(encoding="utf-8") as handle:
        documents = [row["doc"] for row in csv.DictReader(handle)]
    lines = ["# The 4 PAVE documents: automatic check of every tool's output", "",
             "veraPDF PDF/UA-1 and the share of the text that is tagged (the rest is decoration or not tagged at all), "
             "checked exactly like all other outputs. Built by `evaluation/pave_auto_check.py`.", "",
             "| Tool | Pass PDF/UA | Problems per document (1, 2, 3, 4) | Total | Rules failing | Tagged text per document |",
             "|---|---|---|---|---|---|"]
    for tool, name in TOOLS.items():
        results = []
        for doc in documents:
            target = CHECKS / tool / f"{doc}.json"
            output = WORK / "pave" / "outputs" / tool / f"{doc}.pdf"
            if not target.exists() and output.exists():
                subprocess.run([str(FROZEN_PYTHON), str(HERE / "check_one.py"), str(output), str(target)], check=False)
            results.append(json.loads(target.read_text(encoding="utf-8")) if target.exists() else {})
        if not any(results):
            continue
        rules = collections.Counter()
        for result in results:
            rules.update(result.get("by_rule") or {})
        problems = [result.get("problems") for result in results]
        lines.append(
            f"| {name} | {sum(bool(r.get('passes')) for r in results)} of {len(documents)} "
            f"| {', '.join(str(p) if p is not None else '–' for p in problems)} | {sum(p or 0 for p in problems):,} "
            f"| {len(rules)}: {', '.join(rule for rule, _ in rules.most_common(3))}{', …' if len(rules) > 3 else ''} "
            f"| {', '.join(share(r) for r in results)} |")
    target = RESULTS / "pave" / "auto-check.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(target.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
