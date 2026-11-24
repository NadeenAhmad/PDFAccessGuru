"""
Acrobat Pro (Autotag + tab order, guided action "PDFAccessGuruEval") next to PDFAccessGuru 1.1.0 and
opendataloader-pdf, on the files Acrobat was given: the untagged Kumar and SafeDocs files. Every tool's output is
checked the same way (veraPDF PDF/UA-1 through PDFAccessGuru's veraPDF runner, and the share of text a screen
reader reaches): Acrobat's with acrobat_files.py check (results in work/runs-acrobat), the others by run.py and
baseline_odl.py. The 4 PAVE documents are scored separately (score_pave.py).

    python evaluation/acrobat_summary.py

Writes results/acrobat/files.csv and results/acrobat/summary.md.
"""

from __future__ import annotations

import csv
import json
import statistics
import sys

from paths import ODL_TABLES, RESULTS, RUN_TABLES, WORK

CHECKS = WORK / "runs-acrobat"
OUT = RESULTS / "acrobat"


def table(path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        return {row["run_id"]: row for row in csv.DictReader(handle)}


def main() -> int:
    rows = []
    for set_name in ("kumar", "safedocs"):
        tools = {
            "pdfaccessguru-1.1.0 rules": table(RUN_TABLES / f"{set_name}__rules.csv"),
            "pdfaccessguru-1.1.0 gemma": table(RUN_TABLES / f"{set_name}__gemma.csv"),
            "opendataloader-pdf": table(ODL_TABLES / f"{set_name}__odl.csv"),
        }
        for folder in sorted((CHECKS / set_name).glob("*")):
            check = json.loads((folder / "check.json").read_text(encoding="utf-8"))
            run_id = folder.name
            group = set_name
            rows.append({"run_id": run_id, "group": group, "tool": "acrobat", "ok": check.get("ok"),
                         "passes": check.get("passes"), "problems": check.get("problems"),
                         "tagged_share": check.get("tagged_share"), "pages": check.get("pages")})
            for tool, results in tools.items():
                r = results.get(run_id)
                if not r:
                    rows.append({"run_id": run_id, "group": group, "tool": tool, "ok": False})
                    continue
                odl = tool == "opendataloader-pdf"
                share = r.get("tagged_share" if odl else "tagged_share_after")
                rows.append({"run_id": run_id, "group": group, "tool": tool, "ok": r.get("ok") == "True",
                             "passes": r.get("passes") == "True",
                             "problems": int(r.get("problems" if odl else "problems_after") or 0) if r.get("ok") == "True" else None,
                             "tagged_share": float(share) if share not in (None, "") else None, "pages": None})
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "files.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["run_id", "group", "tool", "ok", "passes", "problems",
                                                    "tagged_share", "pages"])
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Acrobat Pro next to PDFAccessGuru 1.1.0 and opendataloader-pdf (files Acrobat was given)", "",
             "Same check for every output: veraPDF PDF/UA-1 (PDFAccessGuru's veraPDF runner) and the share of text a "
             "screen reader reaches. Acrobat: Autotag document + Set Tab Order Property (Acrobat Pro 26.003.22075). "
             "All files were untagged before.", "",
             "| Files | Tool | Processed | Pass PDF/UA | Problems left (total) | Median problems per file | Median share of text reached |",
             "|---|---|---|---|---|---|---|"]
    for group in ("kumar", "safedocs"):
        for tool in ("acrobat", "pdfaccessguru-1.1.0 rules", "pdfaccessguru-1.1.0 gemma", "opendataloader-pdf"):
            part = [r for r in rows if r["group"] == group and r["tool"] == tool]
            if not part:
                continue
            ok = [r for r in part if r["ok"]]
            problems = [r["problems"] for r in ok if r["problems"] is not None]
            shares = [r["tagged_share"] for r in ok if r["tagged_share"] is not None]
            lines.append(f"| {group} ({len(part)}) | {tool} | {len(ok)} | {sum(1 for r in ok if r['passes'])} | "
                         f"{sum(problems):,} | {statistics.median(problems) if problems else '–'} | "
                         f"{f'{statistics.median(shares):.0%}' if shares else '–'} |")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print((OUT / "summary.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
