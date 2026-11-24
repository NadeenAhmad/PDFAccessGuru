# Evaluation of PDFAccessGuru

This folder holds everything needed to check and repeat the automatic evaluation of PDFAccessGuru:
the scripts, the lists of test files, the result tables and the logs.

- **What was evaluated:** PDFAccessGuru, installed from [PyPI](https://pypi.org/project/pdfaccessguru/). The final run
  was on 13 November 2026.
- **On what:** 316 real PDF files from three public sources (below). The PDFs themselves are not stored here, because
  they are third-party content. `get_data.py` downloads them from their sources and checks each one against its SHA-1.
- **Compared with:** Adobe Acrobat Pro (Autotag), opendataloader-pdf (free automatic tagging), and PAVE 2.0 (CHI 2025).

## Results

**The test files**
- **Kumar benchmark:** 107 short excerpts of research papers from an accessibility benchmark. Many have errors added on purpose.
- **SafeDocs:** 200 PDFs picked at random from the web.
- **PDF/UA Reference Suite:** 9 PDFs that are already accessible.

A file **passes** when the PDF checker veraPDF finds no problem against PDF/UA, the standard for accessible PDF.
**Problems** are the failed checks it reports. Where two numbers are given, the first is without AI and the second with
AI. The AI only writes descriptions of pictures and formulas; everything else is the same.

### 1. Does PDFAccessGuru make files accessible?

| Test set | Files | Passing before | Passing after | Problems before | Problems after |
|---|---|---|---|---|---|
| Kumar benchmark | 107 | 0 | 56 to 62 | 101,020 | 4,929 to 4,789 |
| SafeDocs | 200 | 0 | 146 to 153 | 316,730 | 14,331 to 14,072 |

- No file passed before fixing.
- After fixing, more than half of the Kumar files and about three quarters of the SafeDocs files pass.
- About 95% of the problems are gone.

### 2. Does it break anything?

- **Accessible files stay accessible:** all 9 Reference Suite files still pass and look the same.
- **No file gets worse:** no file fails more kinds of checks after fixing than before.
- **Pages look the same:** no Kumar page looks different. In SafeDocs, 58 of 2,902 pages (in 17 files) do.
- **Text stays the same:** without AI, the text changes on 2 of the 3,407 pages. With AI, it changes on 12 to 22
  pages per set (none in the Reference Suite), because the AI fills in letters for which the font gives no text.

### 3. How does it compare with other tools?

| Files | Acrobat Pro | opendataloader-pdf | PDFAccessGuru |
|---|---|---|---|
| 156 untagged files (Kumar and SafeDocs): passing | 0 | 0 | 107 to 108 |
| All 316 files: passing | not tested ¹ | 11 | 211 (without AI) |
| 4 PAVE documents: passing | 0 of 4 | 0 of 4 | 2 of 4 (PAVE 2.0: 0 of 4) |
| 4 PAVE documents: problems left | 4,551 | 3,862 | 64 (PAVE 2.0: 56) |

¹ Acrobat Pro was tested only on the 156 untagged files (first row). On files that already have tags, its Autotag
would replace the author's tags with its own, so it was not used on them.

- **Acrobat Pro** and **opendataloader-pdf** tag files automatically, like PDFAccessGuru.
- **PAVE 2.0** (CHI 2025) is a research tool in which a person tags the file with AI help. It took about 30 manual
  actions per document.

### 4. Does it fix the errors in the benchmark?

The benchmark's authors added specific errors to some files (5 files per error).
- **Broken links:** fixed in all 5 files.
- **No tags at all:** tags added in all 5.
- **Missing picture descriptions:** none left in 4 of 5 files without AI, and in all 5 with AI.
- **Not fixed:** wrong table structure (0 of 5); wrong tags that the author already set, such as headings tagged as
  normal text (fixed in 1 of 5); and existing descriptions that say nothing, such as "Figure 6".

### 5. What does it cost?

- **Online AI:** USD 0.93 for all files and settings together, less than 1 cent per file.
- **Time:** typically about half a minute per file without AI, and up to a minute with AI, on a 2019 laptop.

The human judgements are added when the judges have finished: the picture descriptions, the PAVE criteria, and the
links, titles and languages.

### Where the results are

| Question | Results |
|---|---|
| 1. Make files accessible | [`results/summary.md`](results/summary.md), per file in [`results/runs/`](results/runs) |
| 2. Break anything | [`results/summary.md`](results/summary.md), per file in `results/runs/*__noharm.csv` |
| 3. Other tools | [`results/acrobat/`](results/acrobat), [`results/opendataloader/`](results/opendataloader), [`results/pave/auto-check.md`](results/pave/auto-check.md) |
| 4. Benchmark errors | [`results/kumar-criteria/summary.md`](results/kumar-criteria/summary.md) |
| 5. Cost and time | [`logs/costs.csv`](logs/costs.csv), and the `seconds` column of every table |

**AI used:** Gemma 4 26B (`google/gemma-4-26b-a4b-it`) on all sets and GPT-6 Luna (`openai/gpt-6-luna`) on the Kumar
set, both online through OpenRouter, with descriptions at the level "standard". The checker is veraPDF 1.30.1.

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
  Kumar file, drawn at random (seed 20261111).

## How to repeat it

**You need:** Python 3.13, [uv](https://docs.astral.sh/uv/), git, and about 7 GB of disk space. `run_all.sh` installs
PDFAccessGuru with Java and veraPDF. Optional: an OpenRouter API key for the AI settings (`OPENROUTER_API_KEY`), Java on
the PATH for opendataloader-pdf, and Acrobat Pro for its baseline.

```sh
# 1. Test files
python evaluation/get_data.py kumar          # git clone at the commit used (1.4 GB)
python evaluation/get_data.py safedocs       # download and unpack 0000.zip (1.3 GB)
python evaluation/get_data.py reference      # explains the download by hand (the site blocks scripts)
python evaluation/get_data.py verify         # every listed file present and unchanged?
python evaluation/get_data.py pave           # the 4 PAVE documents (needs PyMuPDF)

# 2. PDFAccessGuru on every set and setting, then the do-no-harm check (about 6 hours, USD 0.93 online)
WORKERS=3 bash evaluation/run_all.sh
python evaluation/summary.py                 # results/summary.md

# 3. Baselines and criteria
uv venv evaluation/work/venv-odl && VIRTUAL_ENV=evaluation/work/venv-odl uv pip install opendataloader-pdf==2.5.21
python evaluation/baseline_odl.py kumar      # then safedocs and reference (about 15 minutes in total)
python evaluation/acrobat_files.py prepare   # then Acrobat by hand, as described in the script
python evaluation/acrobat_files.py check && python evaluation/acrobat_summary.py
evaluation/work/venv/bin/python evaluation/kumar_criteria.py
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
| [`results/runs/`](results/runs) | One row per file and setting (`SET__SETTING.csv`) and its do-no-harm check (`SET__SETTING__noharm.csv`) |
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
| | `sets.py` | Builds the lists of test files (`results/sets/*.csv`) |
| Run | `run_all.sh` | The whole automatic evaluation: installs PDFAccessGuru from PyPI with pinned libraries (`constraints.txt`), runs every set with every setting, then the do-no-harm check |
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
| | `blip_pictures.py`, `describe_pictures.py` | Descriptions by BLIP (a non-LLM baseline) and by PDFAccessGuru |
| Rating site | `build_rating_netlify.py`, `build_parts_23.py`, `rating_*.html` | The blind rating site for the judges |
