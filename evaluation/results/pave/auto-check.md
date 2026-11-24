# The 4 PAVE documents: automatic check of every tool's output

veraPDF PDF/UA-1 and the share of the text that is tagged (the rest is decoration or not tagged at all), checked exactly like all other outputs. Built by `evaluation/pave_auto_check.py`.

| Tool | Pass PDF/UA | Problems per document (1, 2, 3, 4) | Total | Rules failing | Tagged text per document |
|---|---|---|---|---|---|
| PDFAccessGuru 1.1.0 (Gemma 4 26B) | 2 of 4 | 4, 60, 0, 0 | 64 | 1: 7.21.7-1 | 88%, 91%, 87%, 95% |
| PAVE 2.0 (all automatic buttons, by hand) | 0 of 4 | 21, 27, 7, 1 | 56 | 8: 7.21.7-1, 7.21.4.1-1, 7.21.4.2-2, … | 98%, 96%, 96%, 100% |
| Acrobat Pro (Autotag) | 0 of 4 | 1754, 962, 436, 1399 | 4,551 | 18: 7.2-34, 7.2-21, 7.21.5-1, … | 90%, 73%, 71%, 54% |
| opendataloader-pdf | 0 of 4 | 1162, 825, 435, 1440 | 3,862 | 12: 7.2-34, 7.21.7-1, 7.2-22, … | 96%, 91%, 62%, 54% |
