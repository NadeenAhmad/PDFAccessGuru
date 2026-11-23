"""
Where the evaluation reads test files and writes its outputs. Only results/ is part of the repository.

By default the test files are expected in evaluation/data/ and outputs go to evaluation/work/ (both ignored by git).
Other folders: set PDFACCESSGURU_EVAL_DATA and PDFACCESSGURU_EVAL_WORK.
"""

from __future__ import annotations

import os
from pathlib import Path

# The frozen version that is evaluated (exactly as published on PyPI).
VERSION = os.environ.get("PDFACCESSGURU_EVAL_VERSION", "1.1.0")
_SUFFIX = f"-{VERSION}"

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"                                    # small tables: committed, later published

TESTDATA = Path(os.environ.get("PDFACCESSGURU_EVAL_DATA", HERE / "data"))   # third-party PDFs: never committed
KUMAR = TESTDATA / "kumar-benchmark"                           # github.com/Anukriti12/PDF-Accessibility-Benchmark (CC0)
SAFEDOCS = TESTDATA / "cc-main-2021-31" / "pdfs"               # SafeDocs CC-MAIN-2021-31, file 0000.zip (digitalcorpora.org)
REFERENCE_SUITE = TESTDATA / "pdfua-reference-suite"           # PDF Association, PDF/UA Reference Suite 1.1 (CC BY 4.0)

WORK = Path(os.environ.get("PDFACCESSGURU_EVAL_WORK", HERE / "work"))      # raw outputs: fixed PDFs, full reports, logs
RUNS = WORK / f"runs{_SUFFIX}"
FROZEN_PYTHON = WORK / f"venv-{VERSION}" / "bin" / "python"    # the version exactly as published on PyPI
RUN_TABLES = RESULTS / f"runs{_SUFFIX}"                          # results/runs-1.1.0
ODL_RUNS = WORK / "runs-opendataloader"                     # baseline: opendataloader-pdf outputs (SET/odl/RUN_ID)
ODL_TABLES = RESULTS / "opendataloader"                     # baseline tables: SET__odl.csv
COST_LOG = WORK / "cost-log.csv"                               # every paid AI request, with its price
