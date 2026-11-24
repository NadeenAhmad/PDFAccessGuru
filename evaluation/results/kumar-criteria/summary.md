# Kumar et al.'s criteria: files without the added errors

Cells: files of this criterion and label with **no error left** / files with this version; in brackets the same for the held-out files only (the development set was used while building 1.1). "Failed" files had errors added by Kumar et al.; "not present" files had the element removed; "passed" files are the well-made ones (no harm: they should stay without errors). Acrobat ran on the untagged files only. Not measured automatically: reading order (people judge it in Part 2) and font readability (Kumar et al.'s added errors are smaller text; no tool changes text size). What each criterion counts: see the top of evaluation/kumar_criteria.py.

## Label: failed

| Criterion | original | pdfaccessguru-1.1.0 rules | pdfaccessguru-1.1.0 gemma | pdfaccessguru-1.1.0 luna | opendataloader-pdf | acrobat |
|---|---|---|---|---|---|---|
| alt_text_quality | 3/5 (3/5) | 3/5 (3/5) | 3/5 (3/5) | 3/5 (3/5) | 0/5 (0/5) | – |
| color_contrast | 1/5 (0/3) | 1/5 (0/3) | 1/5 (0/3) | 1/5 (0/3) | 1/5 (0/3) | – |
| functional_hyperlinks | 0/5 (0/3) | 5/5 (3/3) | 5/5 (3/3) | 5/5 (3/3) | 5/5 (3/3) | 5/5 (3/3) |
| semantic_tagging | 0/5 (0/4) | 1/5 (1/4) | 1/5 (1/4) | 1/5 (1/4) | 5/5 (4/4) | – |
| table_structure | 0/5 (0/4) | 0/5 (0/4) | 0/5 (0/4) | 0/5 (0/4) | 1/5 (0/4) | – |

## Label: not_present

| Criterion | original | pdfaccessguru-1.1.0 rules | pdfaccessguru-1.1.0 gemma | pdfaccessguru-1.1.0 luna | opendataloader-pdf | acrobat |
|---|---|---|---|---|---|---|
| alt_text_quality | 1/5 (1/3) | 4/5 (3/3) | 5/5 (3/3) | 5/5 (3/3) | 0/5 (0/3) | – |
| functional_hyperlinks | 5/5 (5/5) | 5/5 (5/5) | 5/5 (5/5) | 5/5 (5/5) | 5/5 (5/5) | – |
| semantic_tagging | 0/5 (0/4) | 5/5 (4/4) | 5/5 (4/4) | 5/5 (4/4) | 5/5 (4/4) | 0/5 (0/4) |
| table_structure | 5/5 (5/5) | 5/5 (5/5) | 5/5 (5/5) | 5/5 (5/5) | 5/5 (5/5) | 2/5 (2/5) |

## Label: passed

| Criterion | original | pdfaccessguru-1.1.0 rules | pdfaccessguru-1.1.0 gemma | pdfaccessguru-1.1.0 luna | opendataloader-pdf | acrobat |
|---|---|---|---|---|---|---|
| color_contrast | 2/5 (2/4) | 2/5 (2/4) | 2/5 (2/4) | 2/5 (2/4) | 2/5 (2/4) | – |
| functional_hyperlinks | 5/5 (2/2) | 5/5 (2/2) | 5/5 (2/2) | 5/5 (2/2) | 5/5 (2/2) | – |
| semantic_tagging | 4/5 (3/4) | 4/5 (3/4) | 4/5 (3/4) | 4/5 (3/4) | 5/5 (4/4) | – |
| table_structure | 5/5 (5/5) | 5/5 (5/5) | 5/5 (5/5) | 5/5 (5/5) | 1/5 (1/5) | – |

## Does the automatic check agree with the experts? (originals)

| Criterion | passed: no error found | failed: errors found |
|---|---|---|
| alt_text_quality | 0/0 | 2/5 |
| color_contrast | 2/5 | 4/5 |
| functional_hyperlinks | 5/5 | 5/5 |
| semantic_tagging | 4/5 | 5/5 |
| table_structure | 5/5 | 5/5 |
