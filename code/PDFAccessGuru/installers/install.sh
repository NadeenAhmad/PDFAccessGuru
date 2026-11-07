#!/bin/sh
# PDFAccessGuru installer for macOS and Linux.
#
#   curl -LsSf https://raw.githubusercontent.com/NadeenAhmad/PDFAccessGuru/main/code/PDFAccessGuru/installers/install.sh | sh
#
# What it does (nothing needs admin rights):
#   1. installs uv, a small program that installs Python tools (only if it is missing),
#   2. installs PDFAccessGuru with its own Python (you do not need Python yourself),
#   3. adds PDFAccessGuru to your Applications folder / app menu.
# Run it again at any time to update. PDFACCESSGURU_SOURCE can point to another package
# source (e.g. a local wheel file) for testing.
set -eu

say() { printf '%s\n' "$*"; }
source_spec="${PDFACCESSGURU_SOURCE:-pdfaccessguru}"

say "Installing PDFAccessGuru ..."

if command -v uv >/dev/null 2>&1; then
    uv_cmd="uv"
elif [ -x "$HOME/.local/bin/uv" ]; then
    uv_cmd="$HOME/.local/bin/uv"
else
    say "Step 1 of 3: installing uv (a small helper that installs Python tools) ..."
    curl -LsSf https://astral.sh/uv/install.sh | sh -s -- --quiet
    uv_cmd="$HOME/.local/bin/uv"
fi

say "Step 2 of 3: installing PDFAccessGuru (this can take a few minutes the first time) ..."
# --no-build: only use ready-made packages, so no compiler is needed on any computer.
"$uv_cmd" tool install --upgrade --no-build --python 3.13 "$source_spec"
"$uv_cmd" tool update-shell >/dev/null 2>&1 || true

tool_bin="$("$uv_cmd" tool dir --bin)"
say "Step 3 of 3: adding PDFAccessGuru to your apps ..."
"$tool_bin/pdfaccessguru" shortcut

say ""
say "Done. Open PDFAccessGuru from your apps (on a Mac: the Applications folder in your home folder)."
say "On the first start it downloads two free helper programs (about 75 MB, once)."
say "You can also use it in a terminal: pdfaccessguru fix your-file.pdf"
