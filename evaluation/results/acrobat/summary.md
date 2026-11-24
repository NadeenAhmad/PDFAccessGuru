# Acrobat Pro next to PDFAccessGuru 1.1.0 and opendataloader-pdf (files Acrobat was given)

Same check for every output: veraPDF PDF/UA-1 (PDFAccessGuru's veraPDF runner) and the share of text a screen reader reaches. Acrobat: Autotag document + Set Tab Order Property (Acrobat Pro 26.003.22075). All files were untagged before.

| Files | Tool | Processed | Pass PDF/UA | Problems left (total) | Median problems per file | Median share of text reached |
|---|---|---|---|---|---|---|
| kumar held out (16) | acrobat | 16 | 0 | 38,956 | 2125.5 | 88% |
| kumar held out (16) | pdfaccessguru-1.1.0 rules | 16 | 6 | 1,260 | 20.5 | 95% |
| kumar held out (16) | pdfaccessguru-1.1.0 gemma | 16 | 6 | 1,238 | 14.0 | 95% |
| kumar held out (16) | opendataloader-pdf | 16 | 0 | 19,204 | 1003.5 | 96% |
| kumar development (4) | acrobat | 4 | 0 | 7,570 | 2217.5 | 94% |
| kumar development (4) | pdfaccessguru-1.1.0 rules | 4 | 1 | 118 | 21.5 | 99% |
| kumar development (4) | pdfaccessguru-1.1.0 gemma | 4 | 1 | 99 | 13.5 | 99% |
| kumar development (4) | opendataloader-pdf | 4 | 0 | 6,039 | 1863.0 | 97% |
| safedocs (136) | acrobat | 136 | 0 | 145,878 | 208.0 | 80% |
| safedocs (136) | pdfaccessguru-1.1.0 rules | 136 | 100 | 11,375 | 0.0 | 99% |
| safedocs (136) | pdfaccessguru-1.1.0 gemma | 136 | 101 | 11,177 | 0.0 | 99% |
| safedocs (136) | opendataloader-pdf | 132 | 0 | 132,782 | 169.0 | 82% |
