# Results of PDFAccessGuru 1.1.0

Original files against the files fixed by PDFAccessGuru, checked with veraPDF (PDF/UA-1). Built by
`evaluation/summary.py` from the per-file tables in `results/runs-1.1.0/`.

| Set | AI for descriptions | Files | Pass PDF/UA (original → fixed) | Problems (original → fixed) | Files with more failing rules | Pages that look different | Pages whose text differs | Pictures sent to AI | Online cost (USD) | Processing time (hours, sum over files) |
|---|---|---|---|---|---|---|---|---|---|---|
| Kumar benchmark | none (simple rules) | 107 | 0 → **56** | 101,020 → **4,929** | 0 | 0 | 0 | 0 | 0.00 | 1.1 |
| Kumar benchmark | Gemma 4 26B | 107 | 0 → **60** | 101,020 → **4,880** | 0 | 0 | 12 | 290 | 0.14 | 1.8 |
| Kumar benchmark | GPT-6 Luna | 107 | 0 → **62** | 101,020 → **4,789** | 0 | 0 | 17 | 290 | 0.30 | 3.2 |
| SafeDocs | none (simple rules) | 200 | 0 → **146** | 316,730 → **14,331** | 0 | 58 | 2 | 0 | 0.00 | 3.6 |
| SafeDocs | Gemma 4 26B | 200 | 0 → **153** | 316,730 → **14,072** | 0 | 58 | 22 | 2,253 | 0.48 | 3.9 |
| Reference Suite | none (simple rules) | 9 | 9 → **9** | 0 → **0** | 0 | 0 | 0 | 0 | 0.00 | 0.0 |
| Reference Suite | Gemma 4 26B | 9 | 9 → **9** | 0 → **0** | 0 | 0 | 0 | 0 | 0.00 | 0.1 |

- *Files with more failing rules*: the fixed file fails more distinct PDF/UA rules than the original.
- *Pages that look different / whose text differs*: `no_harm.py`, independent of the tool's own safeguards.
- The online AI (Gemma 4 26B and GPT-6 Luna through OpenRouter) writes descriptions of pictures and formulas;
  everything else is the same in every setting.
