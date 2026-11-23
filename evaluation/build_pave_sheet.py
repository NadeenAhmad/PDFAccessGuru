"""
The PAVE-style check (comparison with PAVE 2.0, ZHAW, CHI 2025, arXiv 2503.22216): human judges score the tagging of each tool's output on PAVE's 13 criteria (all content tagged, reading order, headings and their
levels, tables and their structure, lists and their structure, figures and their alternative texts, formulas and
their alternative texts, captions). Score per criterion = correct / (correct + wrong or missing), as in PAVE.

Documents: results/pave/selection.csv (4 documents, 3 pages each; evaluation/work/pave/input/DOC.pdf).
Outputs of each tool: evaluation/work/pave/outputs/TOOL/DOC.pdf, for example TOOL = pdfaccessguru-1.1.0,
acrobat, pave, odl. Tools are shown blind ("Version A, B, ..." in a fixed random order per document); the key goes to
evaluation/work/pave/key.json, never into the sheet.

    python3 evaluation/build_pave_sheet.py        (RENDER_PYTHON: a Python with PDFAccessGuru, default the frozen one)

Writes evaluation/work/pave/pave-sheet.html (offline; shows the documents' pages: never committed).
"""

from __future__ import annotations

import csv
import html
import json
import os
import random
import subprocess
from pathlib import Path

from paths import FROZEN_PYTHON, RESULTS, WORK

SEED = 20261112
PAVE = WORK / "pave"
RENDER_PYTHON = os.environ.get("RENDER_PYTHON", str(FROZEN_PYTHON))

# (key, name, what counts as correct, kind): "pages" = judged page by page (yes/no), "count" = elements counted
CRITERIA = [
    ("content", "All content tagged", "On this page, all real content reaches the screen reader (nothing missing; "
     "headers, footers and decoration may be left out).", "pages"),
    ("order", "Reading order", "On this page, the content comes in the order a person reads it (columns, "
     "figures and tables in a sensible place).", "pages"),
    ("headings", "Headings", "Each heading on the pages is tagged as a heading. Wrong: text tagged as a heading that "
     "is not one, or a heading that is not tagged as one (missing).", "count"),
    ("heading_levels", "Heading levels", "Each heading tagged as a heading has the right level (title, section, "
     "subsection; no skipped levels).", "count"),
    ("tables", "Tables", "Each table is tagged as a table. Wrong: missing tables, or other content tagged as a "
     "table.", "count"),
    ("table_structure", "Table structure", "Each tagged table has the right rows and cells, and its header cells are "
     "marked as headers.", "count"),
    ("lists", "Lists", "Each list is tagged as a list. Wrong: missing lists, or other content tagged as a list.",
     "count"),
    ("list_structure", "List structure", "Each tagged list has one item per list item (nested lists inside their "
     "item; the bullet or number as the item's label).", "count"),
    ("figures", "Figures", "Each meaningful picture or chart is tagged as a figure. Wrong: missing figures, "
     "decoration tagged as a figure, or one figure split into many pieces.", "count"),
    ("figure_alt", "Figure descriptions", "Each tagged figure has a description that fits it (true and useful for "
     "someone who cannot see it).", "count"),
    ("formulas", "Formulas", "Each displayed formula (on its own line) is tagged as a formula. Wrong: missing "
     "formulas or other content tagged as a formula.", "count"),
    ("formula_alt", "Formula descriptions", "Each tagged formula has a text that says the formula correctly.",
     "count"),
    ("captions", "Captions", "Each caption of a figure or table is tagged as a caption, next to its figure or "
     "table.", "count"),
]

_RENDER = r'''
import base64, collections, json, sys
from pathlib import Path
import pikepdf, pymupdf
from pdfaccessguru.webapp.preview import preview_html
from pdfaccessguru.pipeline.text_tagging import measure_text_tagging
original, output, target = sys.argv[1:4]
pages = []
with pymupdf.open(original) as doc:
    for page in doc:
        pages.append(base64.b64encode(page.get_pixmap(dpi=80).tobytes("png")).decode("ascii"))
counts = collections.Counter()
with pikepdf.open(output) as pdf:
    root = pdf.Root.get("/StructTreeRoot")
    roles = root.get("/RoleMap") if root is not None else None
    stack = [root.get("/K")] if root is not None else []
    seen = set()
    while stack:
        node = stack.pop()
        if isinstance(node, pikepdf.Array):
            stack.extend(node)
            continue
        if not isinstance(node, pikepdf.Dictionary) or node.get("/S") is None:
            continue
        if node.is_indirect:
            if node.objgen in seen:
                continue
            seen.add(node.objgen)
        tag = str(node.get("/S"))
        if roles is not None and tag in roles:
            tag = str(roles[tag])
        tag = tag.lstrip("/")
        counts[tag] += 1
        if tag in ("Figure", "Formula") and node.get("/Alt") is not None:
            counts[tag + " with description"] += 1
        stack.append(node.get("/K"))
    share = measure_text_tagging(pdf).get("tagged_share")
summary = {"Headings": sum(v for k, v in counts.items() if k == "H" or (k[:1] == "H" and k[1:].isdigit())),
           "Lists": counts["L"], "List items": counts["LI"], "Tables": counts["Table"],
           "Header cells": counts["TH"], "Figures": counts["Figure"],
           "Figures with description": counts["Figure with description"], "Formulas": counts["Formula"],
           "Formulas with description": counts["Formula with description"], "Captions": counts["Caption"],
           "Share of text tagged": None if share is None else f"{share:.0%}"}
Path(target).write_text(json.dumps({"pages": pages, "preview": preview_html(Path(output)), "summary": summary}),
                        encoding="utf-8")
'''


def main() -> int:
    documents = list(csv.DictReader((RESULTS / "pave" / "selection.csv").open(encoding="utf-8")))
    tools = sorted(path.name for path in (PAVE / "outputs").iterdir() if path.is_dir()) if (PAVE / "outputs").exists() else []
    generator = random.Random(SEED)
    cache = PAVE / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    sheets, key, missing = [], {}, []
    for doc_number, document in enumerate(documents, start=1):
        available = [tool for tool in tools if (PAVE / "outputs" / tool / f"{document['doc']}.pdf").exists()]
        missing += [f"{tool}/{document['doc']}" for tool in tools if tool not in available]
        generator.shuffle(available)
        for letter, tool in zip("ABCDEFGH", available):
            code = f"d{doc_number}{letter}"
            key[code] = {"doc": document["doc"], "tool": tool}
            rendered = cache / f"{tool}__{document['doc']}.json"
            output = PAVE / "outputs" / tool / f"{document['doc']}.pdf"
            if not rendered.exists() or rendered.stat().st_mtime < output.stat().st_mtime:
                subprocess.run([RENDER_PYTHON, "-c", _RENDER, str(PAVE / "input" / f"{document['doc']}.pdf"),
                                str(output), str(rendered)], timeout=900, check=True)
            sheets.append((code, doc_number, letter, json.loads(rendered.read_text(encoding="utf-8"))))
    (PAVE / "key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    (PAVE / "pave-sheet.html").write_text(_page(sheets, len(documents)), encoding="utf-8")
    print(f"{len(sheets)} outputs of {len(documents)} documents -> {PAVE / 'pave-sheet.html'}")
    if missing:
        print("missing outputs:", ", ".join(missing))
    return 0


def _criterion_rows(code: str, pages: int) -> str:
    rows = []
    for key, name, explanation, kind in CRITERIA:
        field = f"{code}-{key}"
        if kind == "pages":
            cells = "".join(f'<label><input type="checkbox" name="{field}-p{n}" value="yes"> page {n} correct</label>'
                            for n in range(1, pages + 1))
            inputs = f'<span class="pages-q">{cells}</span>'
        else:
            inputs = (f'<label>correct <input type="number" min="0" max="999" inputmode="numeric" name="{field}-ok"></label>'
                      f'<label>wrong or missing <input type="number" min="0" max="999" inputmode="numeric" name="{field}-bad"></label>'
                      f'<label><input type="checkbox" name="{field}-none" value="yes"> none on these pages</label>')
        rows.append(f'<tr><th scope="row">{html.escape(name)}<span class="explain">{html.escape(explanation)}</span></th>'
                    f'<td>{inputs}</td></tr>')
    return "".join(rows)


def _page(sheets, document_count: int) -> str:
    sections = []
    for code, doc_number, letter, data in sheets:
        pages = "".join(f'<img src="data:image/png;base64,{png}" alt="Page {n} of document {doc_number}">'
                        for n, png in enumerate(data["pages"], start=1))
        preview = data["preview"]
        body = preview.split("<body>", 1)[-1].rsplit("</body>", 1)[0] if "<body>" in preview else preview
        summary = "".join(f"<li>{html.escape(k)}: <strong>{html.escape(str(v))}</strong></li>" for k, v in data["summary"].items())
        sections.append(f"""
<section class="file" id="{code}" aria-labelledby="{code}-h">
  <h2 id="{code}-h">Document {doc_number}, version {letter}</h2>
  <div class="pair">
    <div class="pages"><h3>The original pages</h3>{pages}</div>
    <div class="preview"><h3>What a screen reader reads in this version</h3>
      <details><summary>Tags found automatically (to help counting)</summary><ul>{summary}</ul></details>
      <div class="reader">{body}</div></div>
  </div>
  <table class="score"><caption>Your scores for document {doc_number}, version {letter}</caption>
  <thead><tr><th scope="col">Criterion</th><th scope="col">Your answer</th></tr></thead>
  <tbody>{_criterion_rows(code, len(data["pages"]))}</tbody></table>
  <label class="comment">Comment (optional) <input type="text" name="{code}-comment"></label>
</section>""")
    codes = [code for code, *_ in sheets]
    keys = [key for key, *_ in CRITERIA]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tagging check (PAVE criteria)</title>
<style>
:root {{ --ink:#1b1f24; --muted:#4a5560; --line:#c9d1d9; --accent:#0b5a8a; --soft:#f3f6f9; }}
body {{ font: 16px/1.5 system-ui, -apple-system, Segoe UI, sans-serif; color: var(--ink); background: #fff; margin: 0 auto; max-width: 1400px; padding: 16px; }}
header {{ position: sticky; top: 0; background: #fff; border-bottom: 2px solid var(--line); padding: 8px 0; z-index: 1; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }}
h1 {{ font-size: 1.4rem; margin: 0 16px 0 0; }}
.file {{ border-top: 3px solid var(--accent); margin-top: 32px; }}
.pair {{ display: flex; gap: 16px; align-items: flex-start; }}
.pages, .preview {{ flex: 1 1 50%; min-width: 0; }}
.pages img {{ width: 100%; border: 1px solid var(--line); margin-bottom: 8px; }}
.reader {{ max-height: 1100px; overflow: auto; border: 1px solid var(--line); padding: 8px 12px; background: var(--soft); }}
table.score {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
table.score caption {{ text-align: left; font-weight: 700; padding: 4px 0; }}
table.score th, table.score td {{ border: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }}
table.score th[scope=row] {{ width: 45%; }}
.explain {{ display: block; font-weight: 400; color: var(--muted); font-size: .9rem; }}
table.score td label {{ margin-right: 14px; white-space: nowrap; }}
input[type=number] {{ font: inherit; width: 4.5em; }}
input[type=text] {{ font: inherit; width: 100%; max-width: 700px; }}
button {{ font: inherit; padding: 6px 14px; border: 2px solid var(--accent); background: var(--accent); color: white; border-radius: 6px; cursor: pointer; }}
:focus-visible {{ outline: 3px solid #f0a000; outline-offset: 2px; }}
@media (max-width: 800px) {{ .pair {{ flex-direction: column; }} table.score th[scope=row] {{ width: auto; }} }}
</style></head><body>
<header><h1>Tagging check (PAVE criteria)</h1><span id="progress" aria-live="polite"></span>
<button type="button" id="save">Save my answers (CSV)</button></header>
<main>
<p>{document_count} documents (3 pages each), each tagged by several tools. The versions are shown in a random order
and do not say which tool made them. On the left are the original pages; on the right is what a screen reader reads in
that version, in reading order. For each criterion, count the elements on the pages: <strong>correct</strong>, and
<strong>wrong or missing</strong> (both kinds of mistakes). If the pages have no such element, tick
<em>none on these pages</em>. For the first two criteria, tick each page that is correct. About 5–7 minutes per
version. Your answers are kept in this browser; click <strong>Save my answers</strong> at the end and send the file.</p>
{"".join(sections)}
</main>
<script>
const KEY = "pdfaccessguru-pave-check-v1", CODES = {json.dumps(codes)}, CRITERIA = {json.dumps(keys)};
function collect() {{ const f = {{}}; document.querySelectorAll("main input").forEach(el => {{
  if (el.type === "checkbox") {{ if (el.checked) f[el.name] = "yes"; }} else if (el.value !== "") f[el.name] = el.value; }}); return f; }}
function versionDone(f, code) {{ return CRITERIA.every(k => Object.keys(f).some(n => n.startsWith(code + "-" + k + "-"))); }}
function progress() {{ const f = collect(); const done = CODES.filter(c => versionDone(f, c)).length;
  document.getElementById("progress").textContent = `${{done}} of ${{CODES.length}} versions scored`; }}
function store() {{ try {{ localStorage.setItem(KEY, JSON.stringify(collect())); }} catch (e) {{}} progress(); }}
function load() {{ try {{ const f = JSON.parse(localStorage.getItem(KEY) || "{{}}");
  for (const [n, v] of Object.entries(f)) document.querySelectorAll(`[name="${{n}}"]`).forEach(el => {{
    if (el.type === "checkbox") el.checked = v === "yes"; else el.value = v; }}); }} catch (e) {{}} }}
function save() {{ const f = collect(); const rows = [["code", "field", "value"]];
  for (const [n, v] of Object.entries(f)) {{ const i = n.indexOf("-"); rows.push([n.slice(0, i), n.slice(i + 1), String(v).replaceAll('"', "'")]); }}
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([rows.map(r => r.map(v => `"${{v}}"`).join(",")).join("\\n")], {{type: "text/csv"}}));
  a.download = "pave-check.csv"; a.click(); }}
document.querySelector("main").addEventListener("change", store);
document.querySelector("main").addEventListener("input", store);
document.getElementById("save").addEventListener("click", save);
load(); progress();
</script></body></html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
