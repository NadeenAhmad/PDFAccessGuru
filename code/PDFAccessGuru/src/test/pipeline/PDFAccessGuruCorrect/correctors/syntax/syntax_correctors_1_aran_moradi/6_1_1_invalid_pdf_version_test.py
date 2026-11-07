"""
Rule 6.1-1 says a PDF/UA-1 file must be a PDF 1.x file. The old corrector "fixed" PDF 2.0
files by relabelling them as PDF 1.7. Since Phase 3 a PDF 2.0 file is checked against
PDF/UA-2 instead (the standard written for PDF 2.0), and the relabelling corrector is
switched off.
"""

from pathlib import Path

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import DISABLED_CORRECTORS
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import flavour_for, run_verapdf

PDF_2_0 = str(Path(__file__).resolve().parents[5] / "resources" / "PDFAccessGuru_corpus" / "6.1-t01-fail-a.pdf")
PDF_1_X = str(Path(__file__).resolve().parents[5] / "resources" / "veraPDF_corpus" / "7.5-t01-fail-a.pdf")


def test_pdf_2_0_files_are_checked_against_pdf_ua_2():
    assert flavour_for(PDF_2_0) == "ua2"
    assert flavour_for(PDF_1_X) == "ua1"


def test_pdf_2_0_files_are_not_reported_for_the_pdf_ua_1_version_rule():
    assert all(violation.rule_id != "6.1-1" for violation in run_verapdf(PDF_2_0))


def test_relabelling_corrector_is_switched_off():
    assert "invalid-pdf-version" in DISABLED_CORRECTORS
