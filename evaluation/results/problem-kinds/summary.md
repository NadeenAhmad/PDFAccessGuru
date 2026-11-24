# Which kinds of problems were fixed

Every veraPDF PDF/UA-1 problem, grouped into a few kinds (the rules of each kind are listed at the end). Cells: files with this kind of problem, and in brackets the number of problems. Built by `evaluation/problem_kinds.py`.

- veraPDF counts more font problems after tagging than before, with every tool, although fewer files have them: compare files, not problems, for fonts.
- veraPDF only checks that a picture has a description, not that it is useful. opendataloader-pdf describes every picture as "image 1", "image 2", ...

## Kumar benchmark: files with this kind of problem (and problems)

| Kind | Original (107 files) | PDFAccessGuru, without AI (107 files) | PDFAccessGuru, Gemma 4 26B (107 files) | PDFAccessGuru, GPT-6 Luna (107 files) | opendataloader-pdf (107 files) |
|---|---|---|---|---|---|
| Content that is neither tagged nor marked as decoration (a screen reader may skip it) | 90 (56,867) | 9 (189) | 9 (189) | 9 (189) | 0 (0) |
| Text whose language is not set | 72 (31,902) | 0 (0) | 0 (0) | 0 (0) | 73 (59,859) |
| Document settings: PDF/UA mark, title, tag tree, tab order | 107 (361) | 0 (0) | 0 (0) | 0 (0) | 107 (322) |
| Pictures and formulas without a description | 59 (192) | 10 (11) | 10 (11) | 10 (11) | 0 (0) |
| Links and other annotations: not tagged or without a description | 52 (7,242) | 0 (0) | 0 (0) | 0 (0) | 0 (0) |
| Headings, lists, notes and other tags used wrongly | 31 (314) | 5 (39) | 5 (39) | 5 (39) | 0 (0) |
| Tables: missing or wrong table structure | 12 (13) | 8 (13) | 3 (5) | 3 (5) | 0 (0) |
| Fonts: not embedded, characters without a text value, or inconsistent widths | 69 (4,129) | 27 (4,677) | 27 (4,636) | 25 (4,545) | 69 (5,227) |

## SafeDocs: files with this kind of problem (and problems)

| Kind | Original (200 files) | PDFAccessGuru, without AI (200 files) | PDFAccessGuru, Gemma 4 26B (200 files) | opendataloader-pdf (196 files) |
|---|---|---|---|---|
| Content that is neither tagged nor marked as decoration (a screen reader may skip it) | 154 (208,160) | 3 (2,878) | 3 (2,858) | 2 (10) |
| Text whose language is not set | 113 (102,815) | 0 (0) | 0 (0) | 123 (142,913) |
| Document settings: PDF/UA mark, title, tag tree, tab order | 200 (778) | 0 (0) | 0 (0) | 194 (480) |
| Pictures and formulas without a description | 40 (728) | 0 (0) | 0 (0) | 0 (0) |
| Links and other annotations: not tagged or without a description | 62 (2,016) | 2 (6) | 2 (6) | 1 (1) |
| Headings, lists, notes and other tags used wrongly | 10 (53) | 4 (40) | 3 (38) | 2 (19) |
| Tables: missing or wrong table structure | 20 (1,066) | 11 (43) | 4 (4) | 3 (6) |
| Fonts: not embedded, characters without a text value, or inconsistent widths | 123 (1,114) | 38 (11,364) | 37 (11,166) | 117 (5,164) |

## Reference Suite

No problem of any kind, before or after, in any version (Original, PDFAccessGuru, without AI, PDFAccessGuru, Gemma 4 26B, opendataloader-pdf).

## The 156 untagged files Acrobat Pro was given: files with this kind of problem (and problems)

| Kind | Original (156 files) | Acrobat Pro (156 files) | opendataloader-pdf (152 files) | PDFAccessGuru, without AI (156 files) | PDFAccessGuru, Gemma 4 26B (156 files) |
|---|---|---|---|---|---|
| Content that is neither tagged nor marked as decoration (a screen reader may skip it) | 156 (255,078) | 5 (8,474) | 0 (0) | 3 (175) | 3 (175) |
| Text whose language is not set | 124 (114,108) | 129 (171,911) | 132 (151,179) | 0 (0) | 0 (0) |
| Document settings: PDF/UA mark, title, tag tree, tab order | 156 (789) | 156 (401) | 152 (460) | 0 (0) | 0 (0) |
| Pictures and formulas without a description | 0 (0) | 108 (1,262) | 0 (0) | 0 (0) | 0 (0) |
| Links and other annotations: not tagged or without a description | 58 (4,630) | 94 (3,779) | 0 (0) | 1 (1) | 1 (1) |
| Headings, lists, notes and other tags used wrongly | 1 (35) | 98 (288) | 1 (18) | 1 (36) | 1 (36) |
| Tables: missing or wrong table structure | 0 (0) | 34 (112) | 2 (4) | 0 (0) | 0 (0) |
| Fonts: not embedded, characters without a text value, or inconsistent widths | 92 (1,425) | 120 (6,177) | 88 (6,364) | 45 (12,541) | 44 (12,302) |

## The rules of each kind

| Kind | veraPDF rules (PDF/UA-1 clause and test number) |
|---|---|
| Content that is neither tagged nor marked as decoration (a screen reader may skip it) | 7.1-1 7.1-2 7.1-3 |
| Text whose language is not set | 7.2-2 7.2-21 7.2-22 7.2-23 7.2-24 7.2-25 7.2-29 7.2-30 7.2-31 7.2-32 7.2-33 7.2-34 |
| Document settings: PDF/UA mark, title, tag tree, tab order | 5-1 5-2 5-3 5-4 5-5 6.1-1 6.2-1 7.1-4 7.1-8 7.1-9 7.1-10 7.1-11 7.1-12 7.10-1 7.10-2 7.11-1 7.15-1 7.16-1 7.18.3-1 |
| Pictures and formulas without a description | 7.3-1 7.7-1 |
| Links and other annotations: not tagged or without a description | 7.18.1-1 7.18.1-2 7.18.1-3 7.18.2-1 7.18.4-1 7.18.4-2 7.18.5-1 7.18.5-2 7.18.6.2-1 7.18.6.2-2 7.18.8-1 |
| Headings, lists, notes and other tags used wrongly | 7.1-5 7.1-6 7.1-7 7.2-17 7.2-18 7.2-19 7.2-20 7.2-26 7.2-27 7.2-28 7.2-40 7.4.2-1 7.4.4-1 7.4.4-2 7.4.4-3 7.9-1 7.9-2 7.20-1 7.20-2 |
| Tables: missing or wrong table structure | 7.2-3 7.2-4 7.2-5 7.2-6 7.2-7 7.2-8 7.2-9 7.2-10 7.2-11 7.2-12 7.2-13 7.2-14 7.2-15 7.2-16 7.2-36 7.2-37 7.2-38 7.2-39 7.2-41 7.2-42 7.2-43 7.5-1 7.5-2 |
| Fonts: not embedded, characters without a text value, or inconsistent widths | 7.21.3.1-1 7.21.3.2-1 7.21.3.3-1 7.21.3.3-2 7.21.3.3-3 7.21.4.1-1 7.21.4.1-2 7.21.4.2-1 7.21.4.2-2 7.21.5-1 7.21.6-1 7.21.6-2 7.21.6-3 7.21.6-4 7.21.7-1 7.21.7-2 7.21.8-1 |
