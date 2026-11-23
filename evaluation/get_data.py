"""
Gets the test files of the evaluation from their original sources and checks them against the lists in
results/sets/ (SHA-1 of every file). The files are third-party content: they are never part of this repository.

    python evaluation/get_data.py kumar        # Kumar et al. benchmark, git clone at the exact commit used (1.4 GB)
    python evaluation/get_data.py safedocs     # SafeDocs CC-MAIN-2021-31, file 0000.zip (1.3 GB download, 1,000 PDFs)
    python evaluation/get_data.py reference    # PDF/UA Reference Suite: the site blocks scripts, so this explains
                                               # the download by hand and checks the zip
    python evaluation/get_data.py pave         # the 4 documents of the PAVE comparison (first 3 pages; needs PyMuPDF;
                                               # same pages as ours, only the file ID PyMuPDF writes differs)
    python evaluation/get_data.py verify       # every file of every list present and unchanged?

Folders: see paths.py (default evaluation/data/ and evaluation/work/).
"""

from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

from paths import KUMAR, REFERENCE_SUITE, RESULTS, SAFEDOCS, WORK

KUMAR_REPOSITORY = "https://github.com/Anukriti12/PDF-Accessibility-Benchmark"
KUMAR_COMMIT = "9f176e0806a17ad90e6a9a9a801f4314a13f35f8"          # 16 Jul 2025, the version used (CC0-1.0)
SAFEDOCS_ZIP = ("https://digitalcorpora.s3.amazonaws.com/corpora/files/CC-MAIN-2021-31-PDF-UNTRUNCATED/"
                "zipfiles/0000-0999/0000.zip")
REFERENCE_PAGE = "https://pdfa.org/resource/pdfua-reference-suite/"
REFERENCE_ZIP = "PDFUA-Reference-Files_1-1_2024_02.zip"
REFERENCE_ZIP_SHA1 = "18f840ab4ed43f9e093524d04de2c10464897127"


def sha1(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def kumar() -> None:
    if not (KUMAR / ".git").is_dir():
        KUMAR.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", KUMAR_REPOSITORY, str(KUMAR)], check=True)
    subprocess.run(["git", "-C", str(KUMAR), "checkout", "--quiet", KUMAR_COMMIT], check=True)
    print(f"Kumar benchmark at {KUMAR_COMMIT[:7]} in {KUMAR}")


def safedocs() -> None:
    SAFEDOCS.mkdir(parents=True, exist_ok=True)
    archive = SAFEDOCS.parent / "0000.zip"
    if not archive.is_file():
        print(f"downloading {SAFEDOCS_ZIP} (1.3 GB) ...")
        urllib.request.urlretrieve(SAFEDOCS_ZIP, archive)
    with zipfile.ZipFile(archive) as zipped:
        members = [name for name in zipped.namelist() if name.lower().endswith(".pdf")]
        for name in members:                                     # all 1,000: sets.py draws the 200 from all of them
            target = SAFEDOCS / Path(name).name
            if not target.exists():
                target.write_bytes(zipped.read(name))
    print(f"{len(members)} SafeDocs PDFs in {SAFEDOCS}")


def reference() -> None:
    archive = REFERENCE_SUITE / REFERENCE_ZIP
    if not archive.is_file():
        print(f"Download the PDF/UA Reference Suite 1.1 by hand (the site blocks scripts):\n  {REFERENCE_PAGE}\n"
              f"Save {REFERENCE_ZIP} in {REFERENCE_SUITE}/ and run this command again.")
        return
    found = sha1(archive)
    print(f"{REFERENCE_ZIP}: {'the version used' if found == REFERENCE_ZIP_SHA1 else 'a DIFFERENT version (SHA-1 ' + found + ')'}")
    with zipfile.ZipFile(archive) as zipped:
        for name in zipped.namelist():
            if name.lower().endswith(".pdf") and not Path(name).name.startswith("."):
                target = REFERENCE_SUITE / Path(name).name
                if not target.exists():
                    target.write_bytes(zipped.read(name))
    print(f"PDFs in {REFERENCE_SUITE}")


def pave() -> None:
    """The first 3 pages of 2 Kumar and 2 SafeDocs files (results/pave/selection.csv), saved with PyMuPDF."""
    import pymupdf

    sources = {}
    for set_name, base in (("kumar", KUMAR), ("safedocs", SAFEDOCS)):
        with (RESULTS / "sets" / f"{set_name}.csv").open(encoding="utf-8") as handle:
            sources.update({row["run_id"]: base / row["file"] for row in csv.DictReader(handle) if row["run_id"]})
    target = WORK / "pave" / "input"
    target.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "pave" / "selection.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            with pymupdf.open(sources[row["run_id"]]) as source:
                excerpt = pymupdf.open()
                excerpt.insert_pdf(source, from_page=0, to_page=min(int(row["pages_used"]), source.page_count) - 1)
                excerpt.save(target / f"{row['doc']}.pdf", garbage=0)
            print(f"{row['doc']}: first {row['pages_used']} pages of {row['run_id']}")


def verify() -> int:
    missing = changed = fine = 0
    for set_name, base in (("kumar", KUMAR), ("safedocs", SAFEDOCS), ("reference", REFERENCE_SUITE)):
        with (RESULTS / "sets" / f"{set_name}.csv").open(encoding="utf-8") as handle:
            rows = {row["file"]: row["sha1"] for row in csv.DictReader(handle) if row.get("sha1")}
        for name, expected in rows.items():
            path = base / name
            if not path.is_file():
                missing += 1
            elif sha1(path) != expected:
                changed += 1
                print(f"CHANGED: {set_name} {name}")
            else:
                fine += 1
    print(f"{fine} files as in the lists, {changed} changed, {missing} missing")
    return 1 if missing or changed else 0


if __name__ == "__main__":
    steps = {"kumar": kumar, "safedocs": safedocs, "reference": reference, "pave": pave, "verify": verify}
    if len(sys.argv) != 2 or sys.argv[1] not in steps:
        sys.exit(__doc__)
    sys.exit(steps[sys.argv[1]]() or 0)
