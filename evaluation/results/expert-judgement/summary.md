# Expert judgement

Two judges (A, B) rated every item on their own, without knowing which tool made which version. Built by `evaluation/score_expert.py` from the answers in this folder.

## Part 1: picture descriptions (40 pictures)

*Describes the picture well*: rated 4 or 5 for "How helpful is it for someone who cannot see the picture?" (1 = not at all, 5 = very).

| Written by | Describes the picture well: judge A | judge B | both judges | Helpfulness, mean (1–5): judge A | judge B | both |
|---|---|---|---|---|---|---|
| PDFAccessGuru without AI (simple rules) | 8% | 12% | **2%** | 1.75 | 1.82 | **1.79** |
| BLIP | 10% | 10% | **2%** | 2.02 | 1.77 | **1.90** |
| PDFAccessGuru with AI | 85% | 90% | **82%** | 4.38 | 4.30 | **4.34** |

Agreement of the judges (120 descriptions): *describes the picture well* same answer 87%, kappa 0.71; helpfulness within one point 78%, weighted kappa 0.71.

## Part 2: structure of the 4 PAVE documents (PAVE 2.0's 13 criteria)

Per cent correct: correct / (correct + wrong or missing), summed over the 4 documents; the first two criteria count correct pages. Mean of the two judges; – = no such content in the documents.

| Criterion | Acrobat Pro | opendataloader-pdf | PAVE 2.0 | PDFAccessGuru |
|---|---|---|---|---|
| All content tagged | 83 | 92 | 58 | 100 |
| Reading order | 50 | 50 | 25 | 54 |
| Headings | 11 | 46 | 46 | 37 |
| Heading levels | 11 | 46 | 51 | 59 |
| Tables | 45 | 100 | 50 | 75 |
| Table structure | 10 | 25 | 50 | 33 |
| Lists | 11 | 51 | 3 | 34 |
| List structure | 55 | 93 | 50 | 8 |
| Figures | 14 | 24 | 29 | 71 |
| Figure descriptions | 40 | 0 | 57 | 92 |
| Formulas | 0 | 0 | 75 | 75 |
| Formula descriptions | – | – | 58 | 83 |
| Captions | 22 | 40 | 29 | 100 |
| Average, judge A | 33 | 48 | 51 | 67 |
| Average, judge B | 26 | 46 | 38 | 59 |
| **Average, both judges** | **29** | **47** | **45** | **63** |

Agreement of the judges: on whether a kind of content occurs at all, same answer 85%.

## Part 3: links, titles and language

| Version | Links | Link says where it goes: yes / partly / no (both judges) | judge A | judge B | Documents | Title describes the document (both) | Language right (both) |
|---|---|---|---|---|---|---|---|
| Original | 34 | 1% / 0% / 99% | 3% / 0% / 97% | 0% / 0% / 100% | 18 | 8% | 17% |
| Acrobat Pro | 34 | 13% / 25% / 62% | 3% / 21% / 76% | 24% / 29% / 47% | 18 | 6% | 17% |
| opendataloader-pdf | 32 | 31% / 44% / 25% | 3% / 72% / 25% | 59% / 16% / 25% | 17 | 9% | 18% |
| PAVE 2.0 | 4 | 38% / 38% / 25% | 0% / 75% / 25% | 75% / 0% / 25% | 1 | 100% | 100% |
| PDFAccessGuru | 34 | 50% / 43% / 7% | 29% / 59% / 12% | 71% / 26% / 3% | 18 | 44% | 100% |

PAVE 2.0 was run only on the 4 PAVE documents, so it has few links and one title here.

**Passages marked as another language by PDFAccessGuru** (20): is the passage written in the marked language? judge A: yes 11, no 3, can't tell 6; judge B: yes 13, no 7, can't tell 0.

Agreement of the judges: links same answer 60% (kappa 0.40, 138 link versions); titles same answer 90% (kappa 0.79, 72 document versions).

