# How sure are the differences?

Paired tests on the same files and items: Wilcoxon signed-rank test for numbers, exact McNemar test for yes/no. For the judges, the mean of the two judges per item (yes/no: both judges). p is corrected for all 36 tests together (Holm). Built by `evaluation/significance.py`.

## 1. Before and after fixing: all 316 files

| Comparison | Measure | n | PDFAccessGuru | Other | p (Holm) |
|---|---|---|---|---|---|
| PDFAccessGuru without AI: after vs before | problems (median) | 316 | 0 | 210 | < 0.001 |
| PDFAccessGuru without AI: after vs before | files passing | 316 | 211 | 9 | < 0.001 |
| PDFAccessGuru with AI: after vs before | problems (median) | 316 | 0 | 210 | < 0.001 |
| PDFAccessGuru with AI: after vs before | files passing | 316 | 222 | 9 | < 0.001 |

## 4. Other tools: 156 untagged files

| Comparison | Measure | n | PDFAccessGuru | Other | p (Holm) |
|---|---|---|---|---|---|
| PDFAccessGuru without AI vs Acrobat Pro | problems left (median) | 156 | 0 | 269.5 | < 0.001 |
| PDFAccessGuru without AI vs Acrobat Pro | files passing | 156 | 107 | 0 | < 0.001 |
| PDFAccessGuru without AI vs Acrobat Pro | text a screen reader reaches (median) | 156 | 99% | 81% | < 0.001 |
| PDFAccessGuru without AI vs opendataloader-pdf | problems left (median) | 152 | 0 | 215 | < 0.001 |
| PDFAccessGuru without AI vs opendataloader-pdf | files passing | 152 | 104 | 0 | < 0.001 |
| PDFAccessGuru without AI vs opendataloader-pdf | text a screen reader reaches (median) | 152 | 99% | 85% | < 0.001 |
| PDFAccessGuru with AI vs Acrobat Pro | problems left (median) | 156 | 0 | 269.5 | < 0.001 |
| PDFAccessGuru with AI vs Acrobat Pro | files passing | 156 | 108 | 0 | < 0.001 |
| PDFAccessGuru with AI vs Acrobat Pro | text a screen reader reaches (median) | 156 | 99% | 81% | < 0.001 |
| PDFAccessGuru with AI vs opendataloader-pdf | problems left (median) | 152 | 0 | 215 | < 0.001 |
| PDFAccessGuru with AI vs opendataloader-pdf | files passing | 152 | 105 | 0 | < 0.001 |
| PDFAccessGuru with AI vs opendataloader-pdf | text a screen reader reaches (median) | 152 | 99% | 85% | < 0.001 |

## 4. Other tools: all files opendataloader-pdf processed

| Comparison | Measure | n | PDFAccessGuru | Other | p (Holm) |
|---|---|---|---|---|---|
| PDFAccessGuru without AI vs opendataloader-pdf | problems left (median) | 312 | 0 | 87 | < 0.001 |
| PDFAccessGuru without AI vs opendataloader-pdf | files passing | 312 | 208 | 11 | < 0.001 |
| PDFAccessGuru with AI vs opendataloader-pdf | problems left (median) | 312 | 0 | 87 | < 0.001 |
| PDFAccessGuru with AI vs opendataloader-pdf | files passing | 312 | 219 | 11 | < 0.001 |

## 7. Expert judgement: picture descriptions (40 pictures)

| Comparison | Measure | n | PDFAccessGuru | Other | p (Holm) |
|---|---|---|---|---|---|
| PDFAccessGuru with AI vs PDFAccessGuru without AI | helpfulness (mean, 1–5) | 40 | 4.34 | 1.79 | < 0.001 |
| PDFAccessGuru with AI vs PDFAccessGuru without AI | describes the picture well (both judges) | 40 | 33 | 1 | < 0.001 |
| PDFAccessGuru with AI vs BLIP | helpfulness (mean, 1–5) | 40 | 4.34 | 1.90 | < 0.001 |
| PDFAccessGuru with AI vs BLIP | describes the picture well (both judges) | 40 | 33 | 1 | < 0.001 |

## 7. Expert judgement: structure (13 criteria, 4 documents)

| Comparison | Measure | n | PDFAccessGuru | Other | p (Holm) |
|---|---|---|---|---|---|
| PDFAccessGuru vs Acrobat Pro | per cent correct, per criterion (mean) | 12 | 62 | 29 | 0.031 |
| PDFAccessGuru vs opendataloader-pdf | per cent correct, per criterion (mean) | 12 | 62 | 47 | 0.424 |
| PDFAccessGuru vs PAVE 2.0 | per cent correct, per criterion (mean) | 13 | 63 | 45 | 0.107 |

## 7. Expert judgement: links, titles and language

| Comparison | Measure | n | PDFAccessGuru | Other | p (Holm) |
|---|---|---|---|---|---|
| PDFAccessGuru vs original | link says where it goes (0–2, mean) | 34 | 1.43 | 0.03 | < 0.001 |
| PDFAccessGuru vs original | title describes the document (0–2, mean) | 18 | 1.06 | 0.28 | 0.023 |
| PDFAccessGuru vs original | language right (both judges) | 18 | 18 | 3 | < 0.001 |
| PDFAccessGuru vs Acrobat Pro | link says where it goes (0–2, mean) | 34 | 1.43 | 0.51 | < 0.001 |
| PDFAccessGuru vs Acrobat Pro | title describes the document (0–2, mean) | 18 | 1.06 | 0.19 | 0.023 |
| PDFAccessGuru vs Acrobat Pro | language right (both judges) | 18 | 18 | 3 | < 0.001 |
| PDFAccessGuru vs opendataloader-pdf | link says where it goes (0–2, mean) | 32 | 1.42 | 1.06 | 0.001 |
| PDFAccessGuru vs opendataloader-pdf | title describes the document (0–2, mean) | 17 | 1.00 | 0.29 | 0.031 |
| PDFAccessGuru vs opendataloader-pdf | language right (both judges) | 17 | 17 | 3 | < 0.001 |
