import shutil
from pathlib import Path

import pytest

from pdfaccessguru import cli

FIXTURE = Path(__file__).resolve().parent / "resources" / "veraPDF_corpus" / "7.5-t01-fail-a.pdf"


def _run(argv: list[str]) -> int:
    with pytest.raises(SystemExit) as finished:
        cli.main(argv)
    return int(finished.value.code)


def test_version(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert "PDFAccessGuru" in capsys.readouterr().out


def test_check_reports_problems_and_changes_nothing(tmp_path, capsys):
    pdf = tmp_path / "table.pdf"
    shutil.copy(FIXTURE, pdf)
    before = pdf.read_bytes()

    assert _run(["check", str(pdf)]) == cli.EXIT_PROBLEMS
    output = capsys.readouterr().out
    assert "Passes the automatic check: No" in output
    assert pdf.read_bytes() == before


def test_fix_writes_new_file_and_report_next_to_the_original(tmp_path, capsys):
    pdf = tmp_path / "table.pdf"
    shutil.copy(FIXTURE, pdf)
    before = pdf.read_bytes()

    assert _run(["fix", str(pdf)]) == cli.EXIT_OK
    assert (tmp_path / "table_accessible.pdf").is_file()
    assert (tmp_path / "table_accessible_report.md").is_file()
    assert pdf.read_bytes() == before
    assert "Passes the automatic check: Yes" in capsys.readouterr().out


def test_fix_never_replaces_the_original_or_an_existing_file(tmp_path):
    pdf = tmp_path / "table.pdf"
    shutil.copy(FIXTURE, pdf)
    assert _run(["fix", str(pdf), "-o", str(pdf)]) == cli.EXIT_ERROR
    (tmp_path / "table_accessible.pdf").write_bytes(b"keep me")
    assert _run(["fix", str(pdf)]) == cli.EXIT_ERROR
    assert (tmp_path / "table_accessible.pdf").read_bytes() == b"keep me"


def test_missing_file_gives_a_plain_error(tmp_path, capsys):
    assert _run(["check", str(tmp_path / "nope.pdf")]) == cli.EXIT_ERROR
    assert "was not found" in capsys.readouterr().err


def test_fix_a_whole_folder_and_each_report_follows_its_pdf(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PDFACCESSGURU_AI", "none")
    folder = tmp_path / "lectures"
    folder.mkdir()
    shutil.copy(FIXTURE, folder / "one.pdf")
    shutil.copy(FIXTURE, folder / "two.pdf")
    (folder / "notes.txt").write_text("not a PDF")
    assert _run(["fix", str(folder)]) == cli.EXIT_OK
    assert (folder / "one_accessible.pdf").is_file() and (folder / "two_accessible.pdf").is_file()
    output = capsys.readouterr().out
    assert "[2/2]" in output and "Summary:" in output and "the language of the PDF" in output
    # a second run leaves the files made by the tool alone
    assert cli._pdfs_to_fix([str(folder)]) == [(folder / "one.pdf").resolve(), (folder / "two.pdf").resolve()]


def test_output_name_is_only_for_one_file(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "a.pdf")
    shutil.copy(FIXTURE, tmp_path / "b.pdf")
    assert _run(["fix", str(tmp_path / "a.pdf"), str(tmp_path / "b.pdf"), "-o", str(tmp_path / "x.pdf")]) == cli.EXIT_ERROR
