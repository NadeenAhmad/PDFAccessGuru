"""
The main results table of PDFAccessGuru: every set and AI setting, the original files against the fixed ones.
Built only from the per-file tables in results/runs/ (run.py and no_harm.py write them).

    python evaluation/summary.py

Writes results/summary.md.
"""

from __future__ import annotations

import csv
from pathlib import Path

from paths import RESULTS, RUN_TABLES

SETS = [("kumar", "Kumar benchmark"), ("safedocs", "SafeDocs"), ("reference", "Reference Suite")]
SETTINGS = [("rules", "none (simple rules)"), ("gemma", "Gemma 4 26B"), ("luna", "GPT-6 Luna")]


def read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def number(text: str) -> float:
    return float(text) if text not in ("", None) else 0.0


def main() -> int:
    lines = ["# Results of PDFAccessGuru", "",
             "Original files against the files fixed by PDFAccessGuru, checked with veraPDF (PDF/UA-1). Built by",
             "`evaluation/summary.py` from the per-file tables in `results/runs/`.", "",
             "| Set | AI for descriptions | Files | Pass PDF/UA (original → fixed) | Problems (original → fixed) "
             "| Files with more failing rules | Pages that look different | Pages whose text differs "
             "| Pictures sent to AI | Online cost (USD) | Processing time (hours, sum over files) |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for set_name, label in SETS:
        for setting, ai in SETTINGS:
            rows = read(RUN_TABLES / f"{set_name}__{setting}.csv")
            harm = {row["run_id"]: row for row in read(RUN_TABLES / f"{set_name}__{setting}__noharm.csv")}
            if not rows:
                continue
            done = [row for row in rows if row["ok"] == "True"]
            passes_before = sum(number(row["problems_before"]) == 0 for row in done)
            passes_after = sum(row["passes"] == "True" for row in done)
            worse = sum(number(row["rules_after"]) > number(row["rules_before"]) for row in done)
            checked = [harm[row["run_id"]] for row in rows if row["run_id"] in harm]
            look = sum(int(number(h["look_changed_pages"])) for h in checked)
            text = sum(int(number(h["text_changed_pages"])) for h in checked)
            lines.append(
                f"| {label} | {ai} | {len(rows)}{'' if len(done) == len(rows) else f' ({len(done)} processed)'} "
                f"| {passes_before} → **{passes_after}** "
                f"| {int(sum(number(r['problems_before']) for r in done)):,} → **{int(sum(number(r['problems_after']) for r in done)):,}** "
                f"| {worse} | {look} | {text} | {int(sum(number(r['ai_picture']) for r in done)):,} "
                f"| {sum(number(r['cost_usd']) for r in done):.2f} | {sum(number(r['seconds']) for r in rows) / 3600:.1f} |")
    lines += ["", "- *Files with more failing rules*: the fixed file fails more distinct PDF/UA rules than the original.",
              "- *Pages that look different / whose text differs*: `no_harm.py`, independent of the tool's own safeguards.",
              "- The online AI (Gemma 4 26B and GPT-6 Luna through OpenRouter) writes descriptions of pictures and formulas;",
              "  everything else is the same in every setting."]
    target = RESULTS / "summary.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(target.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
