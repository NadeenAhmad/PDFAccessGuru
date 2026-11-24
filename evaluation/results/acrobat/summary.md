# Acrobat Pro next to PDFAccessGuru 1.1.0 and opendataloader-pdf (files Acrobat was given)

Same check for every output: veraPDF PDF/UA-1 (PDFAccessGuru's veraPDF runner) and the share of text a screen reader reaches. Acrobat: Autotag document + Set Tab Order Property (Acrobat Pro 26.003.22075). All files were untagged before.

| Files | Tool | Processed | Pass PDF/UA | Problems left (total) | Median problems per file | Median share of text reached |
|---|---|---|---|---|---|---|
| kumar (20) | acrobat | 20 | 0 | 46,526 | 2125.5 | 90% |
| kumar (20) | pdfaccessguru-1.1.0 rules | 20 | 7 | 1,378 | 20.5 | 96% |
| kumar (20) | pdfaccessguru-1.1.0 gemma | 20 | 7 | 1,337 | 13.5 | 96% |
| kumar (20) | opendataloader-pdf | 20 | 0 | 25,243 | 1272.5 | 97% |
| safedocs (136) | acrobat | 136 | 0 | 145,878 | 208.0 | 80% |
| safedocs (136) | pdfaccessguru-1.1.0 rules | 136 | 100 | 11,375 | 0.0 | 99% |
| safedocs (136) | pdfaccessguru-1.1.0 gemma | 136 | 101 | 11,177 | 0.0 | 99% |
| safedocs (136) | opendataloader-pdf | 132 | 0 | 132,782 | 169.0 | 82% |
