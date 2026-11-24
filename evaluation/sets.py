"""
Builds the lists of test files (results/sets/*.csv). The lists hold names, checksums and simple facts,
never the files themselves, so others can rebuild the same sets from the original sources.

    python evaluation/sets.py         (after get_data.py; needs pikepdf)
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path

import pikepdf

from paths import KUMAR, REFERENCE_SUITE, RESULTS, SAFEDOCS

SAFEDOCS_SAMPLE = 200
SAFEDOCS_SEED = 20261110            # fixed, so the same 200 files are drawn every time


def _facts(path: Path) -> dict:
    facts = {"sha1": hashlib.sha1(path.read_bytes()).hexdigest(), "pages": "", "tagged": "", "encrypted": "", "opens": "no"}
    try:
        with pikepdf.open(path) as pdf:
            facts.update(pages=len(pdf.pages), tagged="/StructTreeRoot" in pdf.Root, encrypted=pdf.is_encrypted, opens="yes")
    except Exception as error:                      # broken files stay in the set: real-world PDFs are like that
        facts["opens"] = f"no: {type(error).__name__}"
    return facts


def _write(name: str, rows: list[dict]) -> None:
    target = RESULTS / "sets" / f"{name}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"{name}: {len(rows)} rows -> {target.relative_to(RESULTS.parent)}")


def kumar() -> None:
    """All entries of the benchmark (criterion, expert label). Identical files are run once (same sha1)."""
    tasks = json.loads((KUMAR / "data" / "dataset.json").read_text(encoding="utf-8"))["tasks"]
    rows = []
    for criterion, labels in tasks.items():
        for label, documents in labels.items():
            for document in documents:
                path = KUMAR / document["pdf_path"]
                row = {"entry": f"{criterion}/{label}/{document['openalex_id']}", "criterion": criterion, "label": label,
                       "openalex_id": document["openalex_id"], "file": document["pdf_path"], "available": path.is_file()}
                row.update(_facts(path) if path.is_file() else {"sha1": "", "pages": "", "tagged": "", "encrypted": "", "opens": "missing"})
                row["run_id"] = f"kumar-{row['sha1'][:12]}" if row["sha1"] else ""
                rows.append(row)
    _write("kumar", rows)


def safedocs() -> None:
    names = sorted(path.name for path in SAFEDOCS.glob("*.pdf"))
    chosen = sorted(random.Random(SAFEDOCS_SEED).sample(names, SAFEDOCS_SAMPLE))
    rows = []
    for name in chosen:
        row = {"file": name, **_facts(SAFEDOCS / name)}
        row["run_id"] = f"safedocs-{Path(name).stem}"
        rows.append(row)
    _write("safedocs", rows)


def reference_suite() -> None:
    files = sorted(REFERENCE_SUITE.rglob("*.pdf")) if REFERENCE_SUITE.is_dir() else []
    if not files:
        print(f"reference suite: no PDFs in {REFERENCE_SUITE} yet (download it from pdfa.org by hand)")
        return
    rows = []
    for path in files:
        row = {"file": str(path.relative_to(REFERENCE_SUITE)), **_facts(path)}
        row["run_id"] = f"reference-{row['sha1'][:12]}"
        rows.append(row)
    _write("reference", rows)


if __name__ == "__main__":
    kumar()
    safedocs()
    reference_suite()
