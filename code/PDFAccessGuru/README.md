# PDFAccessGuru: code

This folder is the Python package `pdfaccessguru`. For using the tool, see the
[main README](../../README.md).

## Set up

You need Python 3.12 or 3.13.

```sh
cd code/PDFAccessGuru
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pdfaccessguru doctor --install       # downloads Java and veraPDF into your user folder
```

Optional AI: copy `.env.example` to `.env` and add a key (`OPENAI_API_KEY` or `OPENROUTER_API_KEY`),
or install [Ollama](https://ollama.com) and run `ollama pull gemma3:4b`.
Never put a key into a source file, a test or a commit.

## Run

```sh
pdfaccessguru app                    # the browser app
pdfaccessguru fix file.pdf           # the command line
```

## Test

```sh
PDFACCESSGURU_AI=none python -m pytest src/test -n auto -q \
  --ignore=src/test/thesis_set --ignore=src/test/Prof_pdf_set --ignore=src/test/validation_set
```

Some tests need test files that cannot be published (theses and other third-party PDFs);
they are skipped when those files are missing.

## How it works

1. **Check:** veraPDF checks the file against PDF/UA-1.
2. **Fix in stages:** fonts, structure, content and decoration, meaning, annotations, descriptions,
   language and metadata (`src/pdfaccessguru/pipeline/stages.py`). Every group of fixes is checked
   (`pipeline/transaction.py`) and undone if it makes the file worse or changes how a page looks.
3. **Untagged files** are tagged first (`src/pdfaccessguru/tagging/`).
4. **Beyond the check:** meaning and structure (`pipeline/meaning.py`) and colour contrast
   (`pipeline/contrast.py`, changes colours only when switched on).
5. **Report** in the language of the PDF (`src/pdfaccessguru/reporting/`), and the browser app
   (`src/pdfaccessguru/webapp/`).

## Release

Set `version` in `pyproject.toml`, write `docs/release-notes/vX.Y.Z.md`, merge, then push the tag
`vX.Y.Z`. The release workflow builds the package, publishes it to PyPI and creates the GitHub
release; users then see "A new version is available" in the app.
