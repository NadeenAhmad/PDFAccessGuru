"""
Which kinds of problems were fixed: every veraPDF PDF/UA-1 problem, before and after, grouped into a few plain kinds
(KINDS below lists every one of the 106 rules), for PDFAccessGuru and the baselines.

Sources (raw outputs in evaluation/work/, see paths.py):
  - original files and PDFAccessGuru: the report of every run (report.json: problems found before fixing, and the
    check after fixing). The report names problems in PDFAccessGuru's words; each name stands for exactly one veraPDF
    rule, translated back with PDFAccessGuru's own table. Same veraPDF runner as check_one.py.
  - opendataloader-pdf: check_after.json of every file (baseline_odl.py).
  - Acrobat Pro: check.json of every file (acrobat_files.py check).

    evaluation/work/venv/bin/python evaluation/problem_kinds.py

Writes results/problem-kinds/files.csv (one row per file, version and rule with problems) and
results/problem-kinds/summary.md.
"""

from __future__ import annotations

import collections
import csv
import json
import sys

from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.taxonomy_data_mapping.map_verapdf_violation_to_taxonomy_data import (
    map_rule_id_to_syntax_violation_name,
)

from paths import ODL_RUNS, ODL_TABLES, RESULTS, RUN_TABLES, RUNS, WORK

OUT = RESULTS / "problem-kinds"
ACROBAT_CHECKS = WORK / "runs-acrobat"
SETS = [("kumar", "Kumar benchmark"), ("safedocs", "SafeDocs"), ("reference", "Reference Suite")]

KINDS = {
    "untagged": ("Content that is neither tagged nor marked as decoration (a screen reader may skip it)",
                 "7.1-1 7.1-2 7.1-3"),
    "language": ("Text whose language is not set",
                 "7.2-2 7.2-21 7.2-22 7.2-23 7.2-24 7.2-25 7.2-29 7.2-30 7.2-31 7.2-32 7.2-33 7.2-34"),
    "settings": ("Document settings: PDF/UA mark, title, tag tree, tab order",
                 "5-1 5-2 5-3 5-4 5-5 6.1-1 6.2-1 7.1-4 7.1-8 7.1-9 7.1-10 7.1-11 7.1-12 7.10-1 7.10-2 7.11-1 "
                 "7.15-1 7.16-1 7.18.3-1"),
    "pictures": ("Pictures and formulas without a description", "7.3-1 7.7-1"),
    "links": ("Links and other annotations: not tagged or without a description",
              "7.18.1-1 7.18.1-2 7.18.1-3 7.18.2-1 7.18.4-1 7.18.4-2 7.18.5-1 7.18.5-2 7.18.6.2-1 7.18.6.2-2 "
              "7.18.8-1"),
    "tags": ("Headings, lists, notes and other tags used wrongly",
             "7.1-5 7.1-6 7.1-7 7.2-17 7.2-18 7.2-19 7.2-20 7.2-26 7.2-27 7.2-28 7.2-40 7.4.2-1 7.4.4-1 7.4.4-2 "
             "7.4.4-3 7.9-1 7.9-2 7.20-1 7.20-2"),
    "tables": ("Tables: missing or wrong table structure",
               "7.2-3 7.2-4 7.2-5 7.2-6 7.2-7 7.2-8 7.2-9 7.2-10 7.2-11 7.2-12 7.2-13 7.2-14 7.2-15 7.2-16 7.2-36 "
               "7.2-37 7.2-38 7.2-39 7.2-41 7.2-42 7.2-43 7.5-1 7.5-2"),
    "fonts": ("Fonts: not embedded, characters without a text value, or inconsistent widths",
              "7.21.3.1-1 7.21.3.2-1 7.21.3.3-1 7.21.3.3-2 7.21.3.3-3 7.21.4.1-1 7.21.4.1-2 7.21.4.2-1 7.21.4.2-2 "
              "7.21.5-1 7.21.6-1 7.21.6-2 7.21.6-3 7.21.6-4 7.21.7-1 7.21.7-2 7.21.8-1"),
}
KIND_OF = {rule: kind for kind, (_, rules) in KINDS.items() for rule in rules.split()}
RULE_OF_NAME = {map_rule_id_to_syntax_violation_name(rule): rule for rule in KIND_OF}
VERSIONS = {"original": "Original", "pdfaccessguru-rules": "PDFAccessGuru, without AI",
            "pdfaccessguru-gemma": "PDFAccessGuru, Gemma 4 26B", "pdfaccessguru-luna": "PDFAccessGuru, GPT-6 Luna",
            "opendataloader-pdf": "opendataloader-pdf", "acrobat": "Acrobat Pro"}


def ok_ids(path) -> list[str]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [row["run_id"] for row in csv.DictReader(handle) if row["ok"] == "True"]


def by_rule(names: dict) -> dict:
    return {RULE_OF_NAME[name]: count for name, count in names.items() if count}


def collect() -> tuple[list[dict], dict]:
    rows, files = [], collections.defaultdict(set)              # files: (set, version) -> run_ids processed

    def add(set_name, run_id, version, counts):
        files[(set_name, version)].add(run_id)
        rows.extend({"set": set_name, "run_id": run_id, "version": version, "rule": rule,
                     "kind": KIND_OF.get(rule, "other"), "problems": count}
                    for rule, count in sorted(counts.items()) if count)

    for set_name, _ in SETS:
        for setting in ("rules", "gemma", "luna"):
            for run_id in ok_ids(RUN_TABLES / f"{set_name}__{setting}.csv"):
                report = json.loads((RUNS / set_name / setting / run_id / "report.json").read_text(encoding="utf-8"))
                phases = {phase["name"]: phase for phase in report["phases"] if phase["name"] in ("detection", "verification")}
                if setting == "rules":
                    add(set_name, run_id, "original", by_rule(phases["detection"]["summary"]["violations_by_name"]))
                add(set_name, run_id, f"pdfaccessguru-{setting}", by_rule(phases["verification"]["summary"]["violations_by_name"]))
        for run_id in ok_ids(ODL_TABLES / f"{set_name}__odl.csv"):
            check = json.loads((ODL_RUNS / set_name / "odl" / run_id / "check_after.json").read_text(encoding="utf-8"))
            add(set_name, run_id, "opendataloader-pdf", check.get("by_rule") or {})
        for folder in sorted((ACROBAT_CHECKS / set_name).glob("*")) if set_name != "reference" else []:
            check = json.loads((folder / "check.json").read_text(encoding="utf-8"))
            if check.get("ok"):
                add(set_name, folder.name, "acrobat", check.get("by_rule") or {})
    return rows, files


def tally(rows, keep) -> tuple[dict, dict]:
    problems, files = collections.Counter(), collections.defaultdict(set)
    for row in rows:
        if keep(row):
            problems[row["kind"]] += row["problems"]
            files[row["kind"]].add(row["run_id"])
    return problems, {kind: len(ids) for kind, ids in files.items()}


def main() -> int:
    rows, processed = collect()
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "files.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["set", "run_id", "version", "rule", "kind", "problems"])
        writer.writeheader()
        writer.writerows(rows)

    lines = ["# Which kinds of problems were fixed", "",
             "Every veraPDF PDF/UA-1 problem, grouped into a few kinds (the rules of each kind are listed at the end). "
             "Cells: files with this kind of problem, and in brackets the number of problems. Built by "
             "`evaluation/problem_kinds.py`.", "",
             "- veraPDF counts more font problems after tagging than before, with every tool, although fewer files "
             "have them: compare files, not problems, for fonts.",
             "- veraPDF only checks that a picture has a description, not that it is useful. opendataloader-pdf "
             "describes every picture as \"image 1\", \"image 2\", ...", ""]
    for set_name, label in SETS:
        versions = [v for v in VERSIONS if v != "acrobat" and processed.get((set_name, v))]
        tallies = {v: tally(rows, lambda r, v=v: r["set"] == set_name and r["version"] == v) for v in versions}
        if not any(tallies[v][0] for v in versions):
            lines += [f"## {label}", "", f"No problem of any kind, before or after, in any version "
                      f"({', '.join(VERSIONS[v] for v in versions)}).", ""]
            continue
        lines += [f"## {label}: files with this kind of problem (and problems)", "",
                  "| Kind | " + " | ".join(f"{VERSIONS[v]} ({len(processed[(set_name, v)])} files)" for v in versions) + " |",
                  "|---|" + "---|" * len(versions)]
        for kind, (title, _) in KINDS.items():
            cells = [f"{tallies[v][1].get(kind, 0)} ({tallies[v][0].get(kind, 0):,})" for v in versions]
            lines.append(f"| {title} | " + " | ".join(cells) + " |")
        lines.append("")

    untagged = processed[("kumar", "acrobat")] | processed[("safedocs", "acrobat")]
    versions = ["original", "acrobat", "opendataloader-pdf", "pdfaccessguru-rules", "pdfaccessguru-gemma"]
    counted = {v: {run_id for (s, version), ids in processed.items() if version == v and s != "reference"
                   for run_id in ids} & untagged for v in versions}
    lines += [f"## The {len(untagged)} untagged files Acrobat Pro was given: files with this kind of problem (and problems)", "",
              "| Kind | " + " | ".join(f"{VERSIONS[v]} ({len(counted[v])} files)" for v in versions) + " |",
              "|---|" + "---|" * len(versions)]
    tallies = {v: tally(rows, lambda r, v=v: r["version"] == v and r["run_id"] in counted[v]) for v in versions}
    for kind, (title, _) in KINDS.items():
        lines.append(f"| {title} | " + " | ".join(f"{tallies[v][1].get(kind, 0)} ({tallies[v][0].get(kind, 0):,})"
                                                  for v in versions) + " |")
    lines += ["", "## The rules of each kind", "", "| Kind | veraPDF rules (PDF/UA-1 clause and test number) |", "|---|---|"]
    lines += [f"| {title} | {rules} |" for title, rules in KINDS.values()]
    other = sorted({row["rule"] for row in rows if row["kind"] == "other"})
    if other:
        lines += ["", f"Rules not in any kind: {', '.join(other)}"]
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print((OUT / "summary.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
