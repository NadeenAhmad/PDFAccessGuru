"""
Kumar et al.'s 7 criteria before and after fixing: the automatic part.

Kumar et al. (ASSETS '25, Table 14) built the benchmark's "failed" files by adding specific errors to well-made
files, and its "not present" files by removing an element. For each criterion this script measures exactly those
errors, with the same code for every version of a file: the original and each tool's output. A file counts as
**fixed** for its criterion when none of the added errors is left.

| Criterion | Errors Kumar et al. added (failed) | Measured here |
|---|---|---|
| alt_text_quality | generic descriptions ("Chart"), missing key data | figures without a description or with a generic one (a picture-type word, maybe numbered: "Figure 6", "Flow chart"); figures all gone although the original had some. Missing key data needs people (Part 1) |
| semantic_tagging | misnested headings (h1→h3→h2), list items without a list, Span tags for content | no heading tagged at all, heading levels skipped, LI outside L, Span directly in a block element; untagged document |
| table_structure | header cells tagged TD, missing scope, wrong header-data links | tables without TH, TH without Scope; tables all gone although the original had some |
| functional_hyperlinks | links that don't work or aren't tagged | link annotations without a target or not tagged as Link (a missing Contents description is a PDF/UA rule, 7.18.5, that Kumar et al. do not count: column links_no_description, not an error here) |
| fonts_readability | smaller text (8 pt and less in the failed files; all fonts stay embedded) | not measured: no tool changes text size or font choice; fonts not embedded are counted for information |
| color_contrast | text below WCAG AA contrast | text below AA (PDFAccessGuru's own contrast check; its fix is off by default) |
| logical_reading_order | order that conflicts with the layout | not measured automatically (Kumar et al.: tools report "needs manual check"); judged by people in Part 2 |

The check is first run on the originals: its result should agree with the experts' labels (passed → no error,
failed → errors found). That agreement is reported, so a reader can see how much the automatic check can be trusted.

    evaluation/work/venv-1.1.0/bin/python evaluation/kumar_criteria.py

Writes results/kumar-criteria/files.csv (one row per benchmark entry and version) and results/kumar-criteria/summary.md.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import pikepdf
import pymupdf

from paths import KUMAR, ODL_RUNS, RESULTS, WORK

OUT = RESULTS / "kumar-criteria"
VERSIONS = {
    "original": None,
    "pdfaccessguru-1.1.0 rules": WORK / "runs-1.1.0" / "kumar" / "rules",
    "pdfaccessguru-1.1.0 gemma": WORK / "runs-1.1.0" / "kumar" / "gemma",
    "pdfaccessguru-1.1.0 luna": WORK / "runs-1.1.0" / "kumar" / "luna",
    "opendataloader-pdf": ODL_RUNS / "kumar" / "odl",
    "acrobat": WORK / "acrobat" / "output",
}
GENERIC = re.compile(r"^(an?\s+|the\s+)?(image|picture|photo|photograph|graphic|figure|fig\.?|chart|flow\s?chart|graph|plot|"
                     r"diagram|illustration|screenshot|table|icon|logo|alt|alt text|description|untitled|bild|abbildung|"
                     r"abb\.?|grafik|foto|diagramm)\s*([\d.:]+[a-z]?)?[.:]?$", re.IGNORECASE)
CONTROL = re.compile(r"[\x00-\x1f\x7f]")      # some originals end their descriptions with a NUL character
BLOCKS = {"Document", "Part", "Art", "Sect", "Div", "NonStruct", "BlockQuote"}


def output_of(version: str, run_id: str) -> Path | None:
    folder = VERSIONS[version]
    if folder is None:
        return None
    if version == "acrobat":
        path = folder / f"{run_id}AdobeFix.pdf"
        return path if path.exists() else None
    if version == "opendataloader-pdf":
        found = sorted((folder / run_id).glob("*.pdf"))
        return found[0] if found else None
    path = folder / run_id / "fixed.pdf"
    return path if path.exists() else None


def _role(node, roles) -> str:
    tag, hops = node.get("/S"), 0
    while roles is not None and tag is not None and tag in roles and hops < 10:
        tag, hops = roles[tag], hops + 1
    return str(tag or "").lstrip("/")


def measure(path: Path, contrast: bool) -> dict:
    """The errors of all 7 criteria in one PDF (counts; None where not measurable)."""
    m = {"tagged": False, "untagged_text": None, "figures": 0, "figures_no_alt": 0, "figures_generic_alt": 0,
         "headings": 0, "heading_skips": 0, "li_outside_l": 0, "block_spans": 0, "tables": 0, "tables_no_th": 0, "th_no_scope": 0,
         "links": 0, "links_no_target": 0, "links_untagged": 0, "links_no_description": 0, "fonts_not_embedded": 0,
         "low_contrast": None}
    from pdfaccessguru.pipeline.text_tagging import measure_text_tagging
    with pikepdf.open(path) as pdf:
        tree = pdf.Root.get("/StructTreeRoot")
        link_owners: set = set()
        if tree is not None:
            m["tagged"] = True
            roles = tree.get("/RoleMap")
            levels: list[int] = []
            tables: list[list[str]] = []
            stack, seen = [(tree.get("/K"), "", None)], set()
            while stack:
                node, parent, table = stack.pop()
                if isinstance(node, pikepdf.Array):
                    stack.extend((child, parent, table) for child in reversed(list(node)))
                    continue
                if not isinstance(node, pikepdf.Dictionary):
                    continue
                if node.is_indirect:
                    if node.objgen in seen:
                        continue
                    seen.add(node.objgen)
                if node.get("/Type") == "/OBJR":
                    target = node.get("/Obj")
                    if parent == "Link" and target is not None and target.is_indirect:
                        link_owners.add(target.objgen)
                    continue
                if node.get("/S") is None:
                    continue
                role = _role(node, roles)
                if role == "Figure":
                    m["figures"] += 1
                    alt = " ".join(CONTROL.sub(" ", str(node.get("/Alt", "") or "")).split())
                    if not alt:
                        m["figures_no_alt"] += 1
                    elif GENERIC.match(alt):
                        m["figures_generic_alt"] += 1
                elif re.fullmatch(r"H[1-6]", role):
                    levels.append(int(role[1]))
                    m["headings"] += 1
                elif role == "LI" and parent != "L":
                    m["li_outside_l"] += 1
                elif role == "Span" and parent in BLOCKS:
                    m["block_spans"] += 1
                elif role == "Table":
                    m["tables"] += 1
                    table = []
                    tables.append(table)
                elif role in ("TH", "TD") and table is not None:
                    table.append(role)
                    if role == "TH":
                        attributes = node.get("/A")
                        items = list(attributes) if isinstance(attributes, pikepdf.Array) else [attributes] if attributes is not None else []
                        if not any(isinstance(a, pikepdf.Dictionary) and a.get("/Scope") is not None for a in items) \
                                and node.get("/Headers") is None:
                            m["th_no_scope"] += 1
                kids = node.get("/K")
                if kids is not None:
                    stack.append((kids, role, table))
            for previous, level in zip(levels, levels[1:]):
                if level > previous + 1:
                    m["heading_skips"] += 1
            m["tables_no_th"] = sum(1 for t in tables if "TH" not in t)
        share = measure_text_tagging(pdf)
        m["untagged_text"] = share.get("untagged", 0)
        for page in pdf.pages:
            for annotation in page.obj.get("/Annots") or []:
                if not isinstance(annotation, pikepdf.Dictionary) or annotation.get("/Subtype") != "/Link":
                    continue
                m["links"] += 1
                action = annotation.get("/A")
                has_target = annotation.get("/Dest") is not None or (
                    isinstance(action, pikepdf.Dictionary) and action.get("/S") is not None
                    and (action.get("/S") != "/URI" or str(action.get("/URI", "")).strip()))
                m["links_no_target"] += not has_target
                m["links_untagged"] += not (annotation.is_indirect and annotation.objgen in link_owners)
                m["links_no_description"] += not str(annotation.get("/Contents", "") or "").strip()
    with pymupdf.open(path) as doc:
        fonts = {}
        for page in doc:
            for xref, ext, kind, *_ in page.get_fonts(full=False):
                fonts[xref] = (ext, kind)
        m["fonts_not_embedded"] = sum(1 for ext, kind in fonts.values() if ext == "n/a" and kind != "Type3")
    if contrast:
        from pdfaccessguru.pipeline.contrast import find_low_contrast
        m["low_contrast"] = len(find_low_contrast(path.read_bytes())[0])
    return m


def errors(criterion: str, m: dict, original: dict | None) -> int | None:
    """Errors of one criterion that are left; None = not measured automatically. `original`: the original file's
    measures (None for the original itself), so a tool that drops all figures or tables does not count as a fix."""
    def all_gone(kind: str) -> int:
        return int(original is not None and original[kind] > 0 and m[kind] == 0)
    if criterion == "alt_text_quality":
        return m["figures_no_alt"] + m["figures_generic_alt"] + all_gone("figures")
    if criterion == "semantic_tagging":
        if not m["tagged"]:
            return 1
        return (0 if m["headings"] else 1) + m["heading_skips"] + m["li_outside_l"] + m["block_spans"]
    if criterion == "table_structure":
        return m["tables_no_th"] + m["th_no_scope"] + all_gone("tables")
    if criterion == "functional_hyperlinks":
        return m["links_no_target"] + m["links_untagged"]
    if criterion == "color_contrast":
        return m["low_contrast"]
    return None


def main() -> int:
    entries = [row for row in csv.DictReader((RESULTS / "sets" / "kumar.csv").open(encoding="utf-8")) if row["run_id"]]
    dev = {row["run_id"] for row in csv.DictReader((RESULTS / "sets" / "dev-1.1.csv").open(encoding="utf-8"))}
    OUT.mkdir(parents=True, exist_ok=True)
    rows, cache = [], {}
    for number, entry in enumerate(entries, start=1):
        base = None
        for version in VERSIONS:
            path = KUMAR / entry["file"] if version == "original" else output_of(version, entry["run_id"])
            if path is None or not path.exists():
                continue
            contrast = entry["criterion"] == "color_contrast"
            key = (str(path), contrast)
            if key not in cache:
                try:
                    cache[key] = measure(path, contrast)
                except Exception as error:
                    print(f"  {version} {entry['run_id']}: {type(error).__name__}: {error}")
                    cache[key] = None
            m = cache[key]
            if m is None:
                continue
            if version == "original":
                base = m
            rows.append({"entry": entry["entry"], "run_id": entry["run_id"], "criterion": entry["criterion"],
                         "label": entry["label"], "set": "development" if entry["run_id"] in dev else "held out",
                         "version": version, "errors": errors(entry["criterion"], m, None if version == "original" else base),
                         **m})
        if number % 10 == 0:
            print(f"  {number} of {len(entries)} entries")
    with (OUT / "files.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (OUT / "summary.md").write_text(summary(rows), encoding="utf-8")
    print((OUT / "summary.md").read_text(encoding="utf-8"))
    return 0


def summary(rows: list[dict]) -> str:
    by = defaultdict(list)
    for row in rows:
        by[(row["criterion"], row["label"], row["version"])].append(row)
    criteria = sorted({row["criterion"] for row in rows})
    versions = [v for v in VERSIONS if any(row["version"] == v for row in rows)]
    lines = ["# Kumar et al.'s criteria: files without the added errors", "",
             "Cells: files of this criterion and label with **no error left** / files with this version; in brackets "
             "the same for the held-out files only (the development set was used while building 1.1). "
             "\"Failed\" files had errors added by Kumar et al.; \"not present\" files had the element removed; "
             "\"passed\" files are the well-made ones (no harm: they should stay without errors). Acrobat ran on the "
             "untagged files only. Not measured automatically: reading order (people judge it in Part 2) and font "
             "readability (Kumar et al.'s added errors are smaller text; no tool changes text size). What each "
             "criterion counts: see the top of evaluation/kumar_criteria.py.", ""]
    for label in ("failed", "not_present", "passed"):
        lines += [f"## Label: {label}", "", "| Criterion | " + " | ".join(versions) + " |",
                  "|---|" + "---|" * len(versions)]
        for criterion in criteria:
            cells = []
            for version in versions:
                group = [r for r in by[(criterion, label, version)] if r["errors"] is not None]
                held = [r for r in group if r["set"] == "held out"]
                cells.append(f"{sum(1 for r in group if r['errors'] == 0)}/{len(group)} "
                             f"({sum(1 for r in held if r['errors'] == 0)}/{len(held)})" if group else "–")
            if any(c != "–" for c in cells):
                lines.append(f"| {criterion} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## Does the automatic check agree with the experts? (originals)", "",
              "| Criterion | passed: no error found | failed: errors found |", "|---|---|---|"]
    for criterion in criteria:
        passed = [r for r in by[(criterion, "passed", "original")] if r["errors"] is not None]
        failed = [r for r in by[(criterion, "failed", "original")] if r["errors"] is not None]
        if passed or failed:
            lines.append(f"| {criterion} | {sum(1 for r in passed if r['errors'] == 0)}/{len(passed)} | "
                         f"{sum(1 for r in failed if r['errors'])}/{len(failed)} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
