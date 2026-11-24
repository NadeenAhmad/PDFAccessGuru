# Results of PDFAccessGuru 1.1.0

Original files against the files fixed by PDFAccessGuru, checked with veraPDF (PDF/UA-1). Built by
`evaluation/summary.py` from the per-file tables in `results/runs-1.1.0/`.

| Set | AI for descriptions | Files | Pass PDF/UA (original → fixed) | Problems (original → fixed) | Files with more failing rules | Pages that look different | Pages whose text differs | Pictures sent to AI | Online cost (USD) | Processing time (hours, sum over files) |
|---|---|---|---|---|---|---|---|---|---|---|
| Kumar, held out | none (simple rules) | 87 | 0 → **43** | 69,705 → **4,462** | 0 | 0 | 0 | 0 | 0.00 | 0.9 |
| Kumar, held out | Gemma 4 26B | 87 | 0 → **46** | 69,705 → **4,433** | 0 | 0 | 7 | 215 | 0.10 | 1.4 |
| Kumar, held out | GPT-6 Luna | 87 | 0 → **47** | 69,705 → **4,367** | 0 | 0 | 11 | 215 | 0.22 | 2.4 |
| Kumar, development set | none (simple rules) | 20 | 0 → **13** | 31,315 → **467** | 0 | 0 | 0 | 0 | 0.00 | 0.2 |
| Kumar, development set | Gemma 4 26B | 20 | 0 → **14** | 31,315 → **447** | 0 | 0 | 5 | 75 | 0.04 | 0.4 |
| Kumar, development set | GPT-6 Luna | 20 | 0 → **15** | 31,315 → **422** | 0 | 0 | 6 | 75 | 0.09 | 0.8 |
| SafeDocs | none (simple rules) | 200 | 0 → **146** | 316,730 → **14,331** | 0 | 58 | 2 | 0 | 0.00 | 3.6 |
| SafeDocs | Gemma 4 26B | 200 | 0 → **153** | 316,730 → **14,072** | 0 | 58 | 22 | 2,253 | 0.48 | 3.9 |
| Reference Suite | none (simple rules) | 9 | 9 → **9** | 0 → **0** | 0 | 0 | 0 | 0 | 0.00 | 0.0 |
| Reference Suite | Gemma 4 26B | 9 | 9 → **9** | 0 → **0** | 0 | 0 | 0 | 0 | 0.00 | 0.1 |

- *Files with more failing rules*: the fixed file fails more distinct PDF/UA rules than the original.
- *Pages that look different / whose text differs*: `no_harm.py`, independent of the tool's own safeguards.
- The online AI (Gemma 4 26B and GPT-6 Luna through OpenRouter) writes descriptions of pictures and formulas;
  everything else is the same in every setting.
