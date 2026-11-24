# Evaluation of PDFAccessGuru 1.1.0

This folder holds everything needed to check and repeat the automatic evaluation of PDFAccessGuru:
the scripts, the lists of test files, the result tables and the logs.

- **What was evaluated:** PDFAccessGuru **1.1.0**, exactly as published on [PyPI](https://pypi.org/project/pdfaccessguru/1.1.0/),
  frozen for the whole evaluation. The final run was on 13 November 2026.
- **On what:** 316 real PDF files from three public sources (below). The PDFs themselves are not stored here, because
  they are third-party content. `get_data.py` downloads them from their sources and checks each one against its SHA-1.
- **Compared with:** Adobe Acrobat Pro (Autotag), opendataloader-pdf (free automatic tagging), and PAVE 2.0 (CHI 2025).

## Results at a glance

**Fixing files.** A file *passes* when veraPDF finds no problem against PDF/UA-1, the standard for accessible PDF.
*Problems* are the failed checks veraPDF reports. Full table: [`results/summary.md`](results/summary.md).

| Set | Files | Pass (original → fixed) | Problems (original → fixed) | Pages that look different after fixing |
|---|---|---|---|---|
| Kumar benchmark, held out | 87 | 0 → 43 to 47 | 69,705 → 4,367 to 4,462 | 0 |
| SafeDocs (web PDFs) | 200 | 0 → 146 to 153 | 316,730 → 14,072 to 14,331 | 58 (on 17 files) |
| PDF/UA Reference Suite (already accessible) | 9 | 9 → 9 | 0 → 0 | 0 |

Ranges: without AI to with AI. The AI only writes descriptions of pictures and formulas. Online AI cost for the whole
run: USD 0.93.

**Compared with other tools** (the same check for every tool):

| Files | Acrobat Pro | opendataloader-pdf | PDFAccessGuru 1.1.0 |
|---|---|---|---|
| 156 untagged files (Kumar and SafeDocs): pass | 0 | 0 | 107 (no AI) to 108 (AI) |
| All 316 files: pass | – | 11 | 211 (no AI) |
| 4 PAVE documents: pass, problems left | 0, 4,551 | 0, 3,862 | 2, 64 (PAVE 2.0: 0, 56, after about 30 manual actions per document) |

**Kumar et al.'s criteria.** These check whether the specific errors that the benchmark's authors added are gone.
Broken links: fixed in 5 of 5 files. Missing structure: added in 5 of 5. Missing picture descriptions: added in 4 of 5
without AI, 5 of 5 with AI. Still open: wrong table structure (fixed in 0 of 5), wrong existing tags (1 of 5), and
existing descriptions that say nothing, such as "Figure 6" (they stay). Full table:
[`results/kumar-criteria/summary.md`](results/kumar-criteria/summary.md).

The human judgements are added when the judges have finished: the picture descriptions, the PAVE criteria, and the
links, titles and languages.

## The experiments

| Question | Test files | What is measured | Results |
|---|---|---|---|
| 1. Does it fix the files? | Kumar (107 files), SafeDocs (200) | PDF/UA-1 pass and problems before and after (veraPDF 1.30.1); share of the text a screen reader reaches | [`summary.md`](results/summary.md), [`runs-1.1.0/`](results/runs-1.1.0) |
| 2. Does it do no harm? | all files, and the Reference Suite (9 well-made files that must stay good) | pages whose text or look changed (`no_harm.py`, independent of the tool's own safeguards); files that fail more rules after fixing | [`summary.md`](results/summary.md), `*__noharm.csv` |
| 3. How does it compare? | the 156 untagged files (Acrobat); all files (opendataloader-pdf); 4 documents (PAVE 2.0) | the same check for every tool's output | [`acrobat/`](results/acrobat), [`opendataloader/`](results/opendataloader), [`pave/auto-check.md`](results/pave/auto-check.md) |
| 4. Does it meet the benchmark's criteria? | Kumar | the errors Kumar et al. added, per criterion, before and after | [`kumar-criteria/`](results/kumar-criteria) |
| 5. What does it cost? | all runs | online AI cost per request, processing time per file | [`logs/costs-1.1.0.csv`](logs/costs-1.1.0.csv), `seconds` in every table |

**Held out.** PDFAccessGuru 1.1 was developed using only a *development set*: 20 Kumar files drawn at random
([`dev-1.1.csv`](results/sets/dev-1.1.csv)). All other files were held out until the final run, and results are
reported separately for both.

**AI settings.** Every set was run without AI (simple rules) and with an online AI through OpenRouter: Gemma 4 26B
(`google/gemma-4-26b-a4b-it`) on all sets, and GPT-6 Luna (`openai/gpt-6-luna`) on the Kumar set. Descriptions were
written at the level "standard". Everything except the descriptions is the same in every setting.

## Test files

| Set | Source | Licence | Used |
|---|---|---|---|
| Kumar | Kumar et al., *Benchmarking PDF Accessibility Evaluation*, ASSETS '25 ([repository](https://github.com/Anukriti12/PDF-Accessibility-Benchmark), commit `9f176e0`) | CC0-1.0 | 120 of the 125 entries (5 PDFs are missing from the repository); 107 distinct files, excerpts of 35 papers |
| SafeDocs | CC-MAIN-2021-31-PDF-UNTRUNCATED, file `0000.zip` ([Digital Corpora](https://digitalcorpora.org/corpora/file-corpora/cc-main-2021-31-pdf-untruncated/)) | as published by the corpus | 200 of its 1,000 files, drawn at random (seed 20261110): 64 tagged, 136 untagged, 2,902 pages |
| Reference Suite | PDF Association, [PDF/UA Reference Suite 1.1](https://pdfa.org/resource/pdfua-reference-suite/) | CC BY 4.0 | all 9 files |

- [`results/sets/`](results/sets): every file with its SHA-1, number of pages and whether it is tagged.
- [`results/pave/selection.csv`](results/pave/selection.csv): the 4 documents of the PAVE comparison (first 3 pages of
  2 Kumar and 2 SafeDocs files).
- [`results/pictures/selection.csv`](results/pictures/selection.csv): the 40 pictures for the human rating, one per
  Kumar file, drawn at random (seed 20261111). They were drawn and captured with PDFAccessGuru 1.0.3, the first frozen
  version, before 1.1 existed.

## How to repeat it

**You need:** Python 3.13, [uv](https://docs.astral.sh/uv/), git, and about 7 GB of disk space. `run_all.sh` installs
PDFAccessGuru 1.1.0 with Java and veraPDF. Optional: an OpenRouter API key for the AI settings (`OPENROUTER_API_KEY`), Java on
the PATH for opendataloader-pdf, and Acrobat Pro for its baseline.

```sh
# 1. Test files
python evaluation/get_data.py kumar          # git clone at the commit used (1.4 GB)
python evaluation/get_data.py safedocs       # download and unpack 0000.zip (1.3 GB)
python evaluation/get_data.py reference      # explains the download by hand (the site blocks scripts)
python evaluation/get_data.py verify         # every listed file present and unchanged?
python evaluation/get_data.py pave           # the 4 PAVE documents (needs PyMuPDF)

# 2. PDFAccessGuru 1.1.0 on every set and setting, then the do-no-harm check (about 6 hours, USD 0.93 online)
VERSION=1.1.0 WORKERS=3 bash evaluation/run_all.sh
python evaluation/summary.py                 # results/summary.md

# 3. Baselines and criteria
uv venv evaluation/work/venv-odl && VIRTUAL_ENV=evaluation/work/venv-odl uv pip install opendataloader-pdf==2.5.21
python evaluation/baseline_odl.py kumar      # then safedocs and reference (about 15 minutes in total)
python evaluation/acrobat_files.py prepare   # then Acrobat by hand, as described in the script
python evaluation/acrobat_files.py check && python evaluation/acrobat_summary.py
evaluation/work/venv-1.1.0/bin/python evaluation/kumar_criteria.py
python evaluation/pave_auto_check.py
```

The times are for the computer used: a MacBook Pro (Intel Core i9-9880H, 8 cores, 32 GB, macOS 15.5), 3 files at a
time. `run.py` can be stopped and started again: it skips files that are done. Online settings check the budget
before every file (`budget.py`, limit EUR 10) and log the exact price of every request.

**How close you will get.** With AI, the descriptions can differ from run to run, so a few numbers may differ. From
the original outputs, the file lists, the Acrobat table and the Kumar-criteria table rebuild identically with these
scripts. The full run was not repeated.

## What is where

| Path | What it holds |
|---|---|
| [`results/summary.md`](results/summary.md) | The main table: every set and AI setting, original against fixed |
| [`results/runs-1.1.0/`](results/runs-1.1.0) | One row per file and setting (`SET__SETTING.csv`) and its do-no-harm check (`SET__SETTING__noharm.csv`) |
| [`results/opendataloader/`](results/opendataloader), [`results/acrobat/`](results/acrobat) | The baselines, per file and summed |
| [`results/kumar-criteria/`](results/kumar-criteria) | Kumar et al.'s criteria per file and tool, and how far the automatic check agrees with the experts' labels |
| [`results/pave/`](results/pave) | The 4 PAVE documents: selection and automatic check per tool |
| [`results/sets/`](results/sets), [`results/pictures/`](results/pictures) | The lists of test files and pictures |
| [`logs/`](logs) | Run logs of the final run, and every paid AI request with its price |

Test files go to `evaluation/data/` and raw outputs (fixed PDFs, full reports) to `evaluation/work/`. Both are ignored
by git; other folders can be set with `PDFACCESSGURU_EVAL_DATA` and `PDFACCESSGURU_EVAL_WORK` (see `paths.py`).

## Scripts

| Step | Script | What it does |
|---|---|---|
| Test files | `get_data.py` | Downloads the test files from their sources and checks them against the lists |
| | `sets.py` | Builds the lists (`results/sets/*.csv`) and draws the development set |
| Run | `run_all.sh` | The whole automatic evaluation: installs the frozen version from PyPI with pinned libraries (`constraints.txt`), runs every set with every setting, then the do-no-harm check |
| | `run.py`, `fix_one.py` | One set with one setting, one process per file; writes the fixed PDF, the report and `result.json` |
| | `budget.py` | Keeps online AI spending under the limit; logs the exact price of every request |
| Do no harm | `no_harm.py` | Compares every fixed PDF with its original: text unchanged, pages look the same |
| Summary | `summary.py` | The main table (`results/summary.md`) from the per-file tables |
| Baselines | `baseline_odl.py` | opendataloader-pdf 2.5.21 on the same files |
| | `acrobat_files.py`, `acrobat_summary.py` | Acrobat Pro on the untagged files: preparation, check, comparison table |
| | `check_one.py` | Checks one PDF exactly like PDFAccessGuru checks its own output |
| Criteria | `kumar_criteria.py` | Kumar et al.'s criteria before and after fixing (the automatic part) |
| PAVE | `pave_auto_check.py` | The automatic check of every tool's output on the 4 documents |
| | `build_pave_sheet.py`, `score_pave.py` | PAVE 2.0's 13 criteria, judged blind by people |
| Pictures | `select_pictures.py`, `capture_pictures.py` | The 40 rated pictures, and exactly what an AI model gets for each |
| | `blip_pictures.py`, `describe_pictures_11.py` | Descriptions by BLIP (a non-LLM baseline) and by PDFAccessGuru 1.1 |
| Rating site | `build_rating_netlify.py`, `build_parts_23.py`, `rating_*.html` | The blind rating site for the judges |
