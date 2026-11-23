# Evaluation of PDFAccessGuru 1.1.0

This folder holds everything needed to repeat the automatic evaluation of PDFAccessGuru 1.1.0 (the version
frozen for the paper): the scripts, the lists of test files, the result tables and the logs. A full guide to the
pipeline, the experiments and the results follows; this page lists the scripts for now.

Test PDFs are never stored here (third-party content): the data scripts download them into `evaluation/data/`.
Raw outputs (fixed PDFs, full reports) go to `evaluation/work/`. Both folders are ignored by git; other locations
can be set with `PDFACCESSGURU_EVAL_DATA` and `PDFACCESSGURU_EVAL_WORK`.

## Scripts

| Step | Script | What it does |
|---|---|---|
| Test sets | `sets.py` | Builds the lists of test files (`results/sets/*.csv`: names, SHA-1, pages, tagged or not) |
| Run | `run_all.sh` | The whole automatic evaluation: installs the frozen version from PyPI, runs every set with every AI setting, then the do-no-harm check |
| | `run.py`, `fix_one.py` | One set with one AI setting, one process per file; writes the fixed PDF, the report and `result.json` |
| | `budget.py` | Keeps online AI spending under the limit (EUR 10); logs the exact price of every request |
| Do no harm | `no_harm.py` | Compares every fixed PDF with its original: text unchanged, pages look the same |
| Baselines | `baseline_odl.py` | opendataloader-pdf 2.5.21 (free automatic tagging) on the same files |
| | `acrobat_files.py`, `acrobat_summary.py` | Acrobat Pro (Autotag + tab order) on the untagged files: preparation, check, comparison table |
| | `check_one.py` | Checks one PDF exactly like PDFAccessGuru checks its own output (veraPDF PDF/UA-1, share of text a screen reader reaches) |
| Kumar's criteria | `kumar_criteria.py` | Kumar et al.'s 7 criteria before and after fixing (automatic part) |
| PAVE comparison | `build_pave_sheet.py`, `score_pave.py` | 4 documents, PAVE 2.0's 13 criteria, judged blind |
| Pictures | `select_pictures.py`, `capture_pictures.py` | Chooses the 40 rated pictures and captures exactly what an AI model gets for each |
| | `blip_pictures.py`, `describe_pictures_11.py` | Descriptions by BLIP (non-LLM baseline) and by PDFAccessGuru 1.1 |
| Rating site | `build_rating_netlify.py`, `build_parts_23.py`, `rating_*.html` | The blind rating site for the judges (pictures, structure, links) |

`paths.py` sets every folder; `constraints.txt` pins the library versions installed with the frozen tool.
