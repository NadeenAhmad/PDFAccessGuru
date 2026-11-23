# Evaluation of PDFAccessGuru 1.1.0

This folder holds everything needed to repeat the automatic evaluation of PDFAccessGuru 1.1.0 (the version
frozen for the paper): the scripts, the lists of test files, the result tables and the logs. A full guide to the
pipeline, the experiments and the results follows; this page lists the scripts for now.

Test PDFs are never stored here (third-party content): the data scripts download them into `evaluation/data/`.
Raw outputs (fixed PDFs, full reports) go to `evaluation/work/`. Both folders are ignored by git; other locations
can be set with `PDFACCESSGURU_EVAL_DATA` and `PDFACCESSGURU_EVAL_WORK`.

## Data

| Set | Source | Licence | Used |
|---|---|---|---|
| Kumar | Kumar et al., *Benchmarking PDF Accessibility Evaluation*, ASSETS '25 ([repository](https://github.com/Anukriti12/PDF-Accessibility-Benchmark), commit `9f176e0`) | CC0-1.0 | 120 of the 125 entries (5 PDFs are missing from the repository), 107 distinct files |
| SafeDocs | CC-MAIN-2021-31-PDF-UNTRUNCATED, file `0000.zip` ([Digital Corpora](https://digitalcorpora.org/corpora/file-corpora/cc-main-2021-31-pdf-untruncated/)) | as published by the corpus | 200 of its 1,000 files, drawn at random (seed 20261110) |
| Reference Suite | PDF Association, [PDF/UA Reference Suite 1.1](https://pdfa.org/resource/pdfua-reference-suite/) | CC BY 4.0 | all 9 files: well-made PDFs that must stay good |

- `results/sets/*.csv` lists every file with its SHA-1, number of pages and whether it is tagged.
- `results/sets/dev-1.1.csv`: the **development set**, 20 Kumar files drawn at random (seed 20261112). Only these were
  used while developing 1.1; all other files were held out until the final run.
- `results/pave/selection.csv`: the 4 documents of the PAVE comparison (first 3 pages of 2 Kumar and 2 SafeDocs files).
- `results/pictures/selection.csv`: the 40 rated pictures (one per Kumar file, drawn at random, seed 20261111).

```sh
python evaluation/get_data.py kumar        # git clone at the commit used (1.4 GB)
python evaluation/get_data.py safedocs     # download and unpack 0000.zip (1.3 GB)
python evaluation/get_data.py reference    # explains the download by hand (the site blocks scripts), then unpacks it
python evaluation/get_data.py verify       # every listed file present and unchanged (SHA-1)?
python evaluation/sets.py                  # optional: rebuilds the lists; they come out identical
python evaluation/get_data.py pave         # the 4 PAVE documents (needs PyMuPDF)
```

## Scripts

| Step | Script | What it does |
|---|---|---|
| Test sets | `get_data.py` | Downloads the test files from their sources and checks them against the lists |
| | `sets.py` | Builds the lists of test files (`results/sets/*.csv`: names, SHA-1, pages, tagged or not) and the development set |
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
