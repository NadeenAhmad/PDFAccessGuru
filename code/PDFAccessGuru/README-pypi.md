# PDFAccessGuru

**Makes PDF files accessible to everyone, including people with disabilities.**

PDFAccessGuru adds what assistive technologies such as screen readers, screen magnifiers and
read-aloud tools need: headings, lists and tables, captions, a reading order, descriptions of pictures,
charts, formulas and links, and the language. It checks the result against PDF/UA, the standard for accessible PDF.

- Runs on your own computer, in your web browser. Your files are not uploaded anywhere, unless you choose an online AI.
- The original file is never changed: you get a new, improved copy and a report in plain words.
- Optional: picture descriptions written by an AI on your computer (Ollama) or online (like ChatGPT), brief, standard or detailed.
- Optional: better colour contrast (off by default, for templates with fixed colours).

## Install

The easiest way is the one-line installer, see
[github.com/NadeenAhmad/PDFAccessGuru](https://github.com/NadeenAhmad/PDFAccessGuru#install).
With [uv](https://docs.astral.sh/uv/):

```sh
uv tool install --no-build pdfaccessguru
pdfaccessguru app
```

## Use

```sh
pdfaccessguru app                    # opens the app in your browser
pdfaccessguru fix your-file.pdf      # writes your-file_accessible.pdf and a report
pdfaccessguru check your-file.pdf    # only checks
```

Licence: GNU Affero General Public License v3.0.
