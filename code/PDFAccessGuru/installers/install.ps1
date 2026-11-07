# PDFAccessGuru installer for Windows.
#
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/NadeenAhmad/PDFAccessGuru/main/code/PDFAccessGuru/installers/install.ps1 | iex"
#
# What it does (nothing needs admin rights):
#   1. installs uv, a small program that installs Python tools (only if it is missing),
#   2. installs PDFAccessGuru with its own Python (you do not need Python yourself),
#   3. adds PDFAccessGuru to the Start menu.
# Run it again at any time to update. PDFACCESSGURU_SOURCE can point to another package
# source (e.g. a local wheel file) for testing.
$ErrorActionPreference = "Stop"
$source = if ($env:PDFACCESSGURU_SOURCE) { $env:PDFACCESSGURU_SOURCE } else { "pdfaccessguru" }

Write-Host "Installing PDFAccessGuru ..."

$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) {
    $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (-not (Test-Path $uv)) {
        Write-Host "Step 1 of 3: installing uv (a small helper that installs Python tools) ..."
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    }
}

Write-Host "Step 2 of 3: installing PDFAccessGuru (this can take a few minutes the first time) ..."
# --no-build: only use ready-made packages, so no compiler is needed on any computer.
& $uv tool install --upgrade --no-build --python 3.13 $source
& $uv tool update-shell | Out-Null

$toolBin = (& $uv tool dir --bin).Trim()
Write-Host "Step 3 of 3: adding PDFAccessGuru to the Start menu ..."
& (Join-Path $toolBin "pdfaccessguru.exe") shortcut

Write-Host ""
Write-Host "Done. Open PDFAccessGuru from the Start menu."
Write-Host "On the first start it downloads two free helper programs (about 75 MB, once)."
Write-Host "You can also use it in a terminal: pdfaccessguru fix your-file.pdf"
