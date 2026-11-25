# Evaluation of PDFAccessGuru

This folder holds everything needed to check and repeat the evaluation of PDFAccessGuru:
the scripts, the lists of test files, the result tables, the logs and the expert judges' answers.

- **What was evaluated:** PDFAccessGuru, installed from [PyPI](https://pypi.org/project/pdfaccessguru/). The final run
  was on 13 November 2026.
- **On what:** 316 real PDF files from three public sources (below). The PDFs themselves are not stored here, because
  they are third-party content. `get_data.py` downloads them from their sources and checks each one against its SHA-1.
- **Compared with:** Adobe Acrobat Pro (Autotag), opendataloader-pdf (free automatic tagging), and PAVE 2.0
  [[4]](#references).

## Results

**The test files**
- **Kumar benchmark** [[1]](#references): 107 short excerpts of research papers from an accessibility benchmark. Many
  have errors added on purpose.
- **SafeDocs** [[2]](#references): 200 PDFs picked at random from the web.
- **PDF/UA Reference Suite** [[3]](#references): 9 PDFs that are already accessible.

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

### 2. Which problems does it fix?

Files with each kind of problem, before → after fixing. The 106 veraPDF rules are grouped into 8 kinds;
[`results/problem-kinds/summary.md`](results/problem-kinds/summary.md) lists the rules of each kind and the number of
problems.

| Kind of problem | Kumar (107 files) | SafeDocs (200 files) |
|---|---|---|
| Content a screen reader may skip (neither tagged nor marked as decoration) | 90 → 9 | 154 → 3 |
| Language of the text not set | 72 → 0 | 113 → 0 |
| Document settings (PDF/UA mark, title, tag tree, tab order) | 107 → 0 | 200 → 0 |
| Links and other annotations not tagged or without a description | 52 → 0 | 62 → 2 |
| Pictures and formulas without a description | 59 → 10 | 40 → 0 |
| Headings, lists and other tags used wrongly | 31 → 5 | 10 → 4 to 3 |
| Tables with missing or wrong structure | 12 → 8 to 3 | 20 → 11 to 4 |
| Fonts (not embedded, characters without a text value) | 69 → 27 to 25 | 123 → 38 to 37 |

- Language and document settings are fixed in every file, links in all but 2. Content a screen reader may skip is
  left in 12 of the 244 files that had it.
- Fonts are what is left most often: of the 105 files that still fail without AI, 56 fail only because of font
  problems.
- veraPDF counts more font problems after fixing than before (5,243 → 16,041 without AI), although fewer files have
  them. This happens with every tool, so this table counts files.
- The Reference Suite has no problem of any kind, before or after.
- veraPDF only checks that a picture has a description, not whether it is useful. The judges rate that in
  [section 7](#7-what-do-expert-judges-say).

### 3. Does it break anything?

- **Accessible files stay accessible:** all 9 Reference Suite files still pass and look the same.
- **No file gets worse:** no file fails more kinds of checks after fixing than before. (2 files have more problems of
  a kind they already had.)
- **Pages look the same:** no Kumar page looks different. In SafeDocs, 58 of 2,902 pages (in 17 files) do.
- **Text stays the same:** without AI, the text changes on 2 of the 3,407 pages. With AI, it changes on 12 to 22
  pages per set (none in the Reference Suite), because the AI fills in letters for which the font gives no text.

### 4. How does it compare with other tools?

| | Acrobat Pro | opendataloader-pdf | PDFAccessGuru |
|---|---|---|---|
| **156 untagged files** (Kumar and SafeDocs) | | | |
| Files passing | 0 | 0 | 107 to 108 |
| Problems left | 192,404 | 158,025 ² | 12,753 to 12,514 |
| Text a screen reader can reach (median per file) | 81% | 85% | 99% |
| **All 316 files** | | | |
| Files passing | not tested ¹ | 11 | 211 to 222 |
| Problems left (417,750 before) | not tested ¹ | 214,001 ² | 19,260 to 18,952 |
| Files with more problems than before | not tested ¹ | 57 | 2 |
| **4 PAVE documents** | | | |
| Files passing | 0 of 4 | 0 of 4 | 2 of 4 (PAVE 2.0: 0 of 4) |
| Problems left | 4,551 | 3,862 | 64 (PAVE 2.0: 56) |

¹ Acrobat Pro was tested only on the 156 untagged files. On files that already have tags, its Autotag would replace
the author's tags with its own, so it was not used on them.
² opendataloader-pdf stopped with an error on 4 untagged SafeDocs files; they are left out of its numbers (406,440
problems before on the 312 files it processed).

**Files with each kind of problem on the 156 untagged files**

| Kind of problem | Before | Acrobat Pro | opendataloader-pdf ² | PDFAccessGuru |
|---|---|---|---|---|
| Content a screen reader may skip | 156 | 5 | 0 | 3 |
| Language of the text not set | 124 | 129 | 132 | 0 |
| Document settings | 156 | 156 | 152 | 0 |
| Links and other annotations | 58 | 94 | 0 | 1 |
| Pictures and formulas without a description | 0 ³ | 108 | 0 ⁴ | 0 |
| Headings, lists and other tags used wrongly | 1 | 98 | 1 | 1 |
| Tables with missing or wrong structure | 0 | 34 | 2 | 0 |
| Fonts | 92 | 120 | 88 | 45 to 44 |

³ Untagged files have no tagged pictures, so veraPDF finds none without a description.
⁴ opendataloader-pdf describes every picture as "image 1", "image 2", and so on, which veraPDF accepts.

- On the same untagged files, PDFAccessGuru leaves about 15 times fewer problems than Acrobat Pro and 12 times fewer
  than opendataloader-pdf. On all 316 files it removes about 95% of the problems; opendataloader-pdf removes about half.
- Acrobat Pro and opendataloader-pdf tag the content, but leave the language and the document settings unset. Acrobat
  Pro also adds pictures without a description and wrongly used tags.
- **Acrobat Pro** and **opendataloader-pdf** tag files automatically, like PDFAccessGuru.
- **PAVE 2.0** [[4]](#references) is a research tool in which a person tags the file with AI help. It took about 30
  manual actions per document.

### 5. Does it fix the errors in the benchmark?

The benchmark's authors added specific errors to some files (5 files per error). Files in which the error is gone:

| Error added | PDFAccessGuru | opendataloader-pdf | Acrobat Pro ¹ |
|---|---|---|---|
| Broken links | 5 | 5 | 5 |
| No tags at all (correct tags added) | 5 | 5 | 0 |
| Missing picture descriptions | 4 (without AI) to 5 (with AI) | 0 | – |
| Wrong tags set by the author, such as skipped heading levels or list items outside a list | 1 | 5 | – |
| Wrong table structure | 0 | 1 | – |
| *No error added:* well-made tables that are still correct | 5 | 1 | – |

- opendataloader-pdf replaces all tags of a file with its own. This removes the author's wrong tags, but it also breaks
  4 of the 5 well-made tables and adds no picture descriptions.
- PDFAccessGuru keeps the tags an author has set. Good tables stay intact, but it fixes few wrong tags.
- **Not fixed by PDFAccessGuru or opendataloader-pdf:** existing descriptions that say nothing, such as "Figure 6".

### 6. What does it cost?

- **Online AI:** USD 0.93 for all files and settings together, less than 1 cent per file.
- **Time:** typically about half a minute per file without AI, and up to a minute with AI, on a 2019 laptop.

### 7. What do expert judges say?

Two judges rated the outputs on their own, without knowing which tool made which version.
[`results/expert-judgement/summary.md`](results/expert-judgement/summary.md) gives each judge's numbers and how far
they agree.
[`rating-site-sample/`](rating-site-sample) shows the rating site exactly as the judges saw it, with 6 of the
Kumar files: the start page, all three parts and their questions.

**Picture descriptions** (the 40 pictures). For each description the judges answered "How helpful is it for someone
who cannot see the picture?" from 1 (not at all) to 5 (very). A description *describes the picture well* when it is
rated 4 or 5.

| Description written by | Describes the picture well (both judges) | Helpfulness (mean, 1–5) |
|---|---|---|
| PDFAccessGuru with AI | **82%** | **4.34** |
| PDFAccessGuru without AI (simple rules) | 2% | 1.79 |
| BLIP (picture captioning, no large language model) | 2% | 1.90 |

- *Both judges* means both rated it 4 or 5. Judge A alone: 85%, 8% and 10%; judge B alone: 90%, 12% and 10%.
- The judges agree well: the same answer for 87% of the 120 descriptions (Cohen's kappa 0.71).

**Structure of the 4 PAVE documents**, judged on PAVE 2.0's 13 criteria [[4]](#references). Per cent correct:
correct / (correct + wrong or missing), summed over the 4 documents; the first two criteria count correct pages.
Mean of the two judges; – means no such content.

| Criterion | Acrobat Pro | opendataloader-pdf | PAVE 2.0 | PDFAccessGuru |
|---|---|---|---|---|
| All content tagged | 83 | 92 | 58 | **100** |
| Reading order | 50 | 50 | 25 | **54** |
| Headings | 11 | **46** | **46** | 37 |
| Heading levels | 11 | 46 | 51 | **59** |
| Tables | 45 | **100** | 50 | 75 |
| Table structure | 10 | 25 | **50** | 33 |
| Lists | 11 | **51** | 3 | 34 |
| List structure | 55 | **93** | 50 | 8 |
| Figures | 14 | 24 | 29 | **71** |
| Figure descriptions | 40 | 0 | 57 | **92** |
| Formulas | 0 | 0 | **75** | **75** |
| Formula descriptions | – | – | 58 | **83** |
| Captions | 22 | 40 | 29 | **100** |
| **Average** | 29 | 47 | 45 | **63** |

- PDFAccessGuru has the highest average, with both judges (judge A: 67, judge B: 59). It is best on tagging all
  content, figures and their descriptions, formulas and captions.
- It is weaker on lists and headings, where opendataloader-pdf does better, and on table structure, where PAVE 2.0
  does better. No tool gets the reading order right on much more than half of the pages.

**Links, titles and language**: 34 links in 18 documents (30 from Kumar and SafeDocs files, 4 from one PAVE
document), and the title and language of each document.

| Version | Link says where it goes: yes / partly / no | Title describes the document | Language right |
|---|---|---|---|
| Original | 1% / 0% / 99% | 8% | 17% |
| Acrobat Pro | 13% / 25% / 62% | 6% | 17% |
| opendataloader-pdf ⁵ | 31% / 44% / 25% | 9% | 18% |
| PDFAccessGuru | **50% / 43% / 7%** | **44%** | **100%** |

⁵ 32 links and 17 documents (it stopped with an error on one file). PAVE 2.0 was run only on the PAVE documents: of
its 4 links, 38% say where they go, 38% partly, 25% not; its title describes the document and its language is right.

- With PDFAccessGuru, 93% of the links tell at least partly where they go; in the originals almost none do.
- PDFAccessGuru sets the right language in every document. Its titles describe the document in 44% of the
  documents, much more often than the other tools, but this is still the weakest point here.
- PDFAccessGuru also marks passages written in another language. Of 20 such passages, judge A found 11 correct, 3
  wrong and could not tell for 6; judge B found 13 correct and 7 wrong.
- The judges agree well on titles (same answer for 90%, kappa 0.79) and moderately on links (60%, kappa 0.40): they
  often differ between "yes" and "partly".

### Where the results are

| Question | Results |
|---|---|
| 1. Make files accessible | [`results/summary.md`](results/summary.md), per file in [`results/runs/`](results/runs) |
| 2. Which problems | [`results/problem-kinds/summary.md`](results/problem-kinds/summary.md), per file and rule in [`results/problem-kinds/files.csv`](results/problem-kinds/files.csv) |
| 3. Break anything | [`results/summary.md`](results/summary.md), per file in `results/runs/*__noharm.csv` |
| 4. Other tools | [`results/acrobat/`](results/acrobat), [`results/opendataloader/`](results/opendataloader), [`results/problem-kinds/summary.md`](results/problem-kinds/summary.md), [`results/pave/auto-check.md`](results/pave/auto-check.md) |
| 5. Benchmark errors | [`results/kumar-criteria/summary.md`](results/kumar-criteria/summary.md) |
| 6. Cost and time | [`logs/costs.csv`](logs/costs.csv), and the `seconds` column of every table |
| 7. Expert judgement | [`results/expert-judgement/summary.md`](results/expert-judgement/summary.md), every answer in [`results/expert-judgement/`](results/expert-judgement) |

**AI used:** Gemma 4 26B (`google/gemma-4-26b-a4b-it`) on all sets and GPT-6 Luna (`openai/gpt-6-luna`) on the Kumar
set, both online through OpenRouter, with descriptions at the level "standard". The checker is veraPDF 1.30.1.

## Test files

| Set | Source | Licence | Used |
|---|---|---|---|
| Kumar | Kumar et al. [[1]](#references) ([repository](https://github.com/Anukriti12/PDF-Accessibility-Benchmark), commit `9f176e0`) | CC0-1.0 | 120 of the 125 entries (5 PDFs are missing from the repository); 107 distinct files, excerpts of 35 papers |
| SafeDocs | CC-MAIN-2021-31-PDF-UNTRUNCATED [[2]](#references), file `0000.zip` ([Digital Corpora](https://digitalcorpora.org/corpora/file-corpora/cc-main-2021-31-pdf-untruncated/)) | as published by the corpus | 200 of its 1,000 files, drawn at random (seed 20261110): 64 tagged, 136 untagged, 2,902 pages |
| Reference Suite | PDF Association, [PDF/UA Reference Suite 1.1](https://pdfa.org/resource/pdfua-reference-suite/) [[3]](#references) | CC BY 4.0 | all 9 files |

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
evaluation/work/venv/bin/python evaluation/problem_kinds.py
python evaluation/pave_auto_check.py
python evaluation/score_expert.py            # the judges' answers -> results/expert-judgement/summary.md
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
| [`results/problem-kinds/`](results/problem-kinds) | Every problem before and after, per file, tool and rule, grouped into 8 kinds |
| [`results/kumar-criteria/`](results/kumar-criteria) | Kumar et al.'s criteria per file and tool, and how far the automatic check agrees with the experts' labels |
| [`results/pave/`](results/pave) | The 4 PAVE documents: selection and automatic check per tool |
| [`results/expert-judgement/`](results/expert-judgement) | The judges' answers (judges A and B; the tool of every version is given) and their scores |
| [`rating-site-sample/`](rating-site-sample) | The rating site as the judges saw it, with 6 Kumar files (answers are not sent anywhere) |
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
| Problem kinds | `problem_kinds.py` | Every problem before and after, grouped into 8 kinds, for every tool |
| Criteria | `kumar_criteria.py` | Kumar et al.'s criteria before and after fixing (the automatic part) |
| PAVE | `pave_auto_check.py` | The automatic check of every tool's output on the 4 documents |
| | `build_pave_sheet.py` | PAVE 2.0's 13 criteria and the pages and screen-reader views the judges see |
| Pictures | `select_pictures.py`, `capture_pictures.py` | The 40 rated pictures, and exactly what an AI model gets for each |
| | `blip_pictures.py`, `describe_pictures.py` | Descriptions by BLIP (a non-LLM baseline) and by PDFAccessGuru |
| Rating site | `build_rating_netlify.py`, `build_parts_23.py`, `rating_*.html` | The blind rating site for the judges |
| Expert judgement | `score_expert.py` | Scores of the judges' answers: pictures, PAVE criteria, links, titles and language |

## References

1. Anukriti Kumar, Tanushree Padath, and Lucy Lu Wang. 2025. Benchmarking PDF Accessibility Evaluation: A Dataset and
   Framework for Assessing Automated and LLM-Based Approaches for Accessibility Testing. In *Proceedings of the 27th
   International ACM SIGACCESS Conference on Computers and Accessibility (ASSETS '25)*. ACM.
   https://doi.org/10.1145/3663547.3746380
2. SafeDocs corpus CC-MAIN-2021-31-PDF-UNTRUNCATED, gathered by NASA's Jet Propulsion Laboratory for DARPA's SafeDocs
   program, hosted by Digital Corpora:
   https://digitalcorpora.org/corpora/file-corpora/cc-main-2021-31-pdf-untruncated/. Background: Timothy Allison,
   Wayne Burke, Chris Mattmann, Anastasia Menshikova, Philip Southam, Ryan Stonebraker, and Virisha Timmaraju. 2020.
   Building a Wide Reach Corpus for Secure Parser Development. In *2020 IEEE Security and Privacy Workshops (SPW)*.
   https://doi.org/10.1109/SPW50608.2020.00066
3. PDF Association. 2024. PDF/UA Reference Suite 1.1. https://pdfa.org/resource/pdfua-reference-suite/
4. Felix M. Schmitt-Koopmann, Elaine M. Huang, Hans-Peter Hutter, and Alireza Darvishy. 2025. Towards More Accessible
   Scientific PDFs for People with Visual Impairments: Step-by-Step PDF Remediation to Improve Tag Accuracy. In
   *Proceedings of the 2025 CHI Conference on Human Factors in Computing Systems (CHI '25)*. ACM.
   https://doi.org/10.1145/3706598.3713084
