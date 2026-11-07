import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[5]
SRC_MAIN_PATH = PROJECT_ROOT / "src"
if str(SRC_MAIN_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_MAIN_PATH))

from pdfaccessguru.exceptions.invalid_pdf_path_exception import InvalidPdfPathException
from pdfaccessguru.exceptions.verapdf_exceptions.verapdf_not_installed_exception import VeraPdfNotInstalledException
from pdfaccessguru.exceptions.verapdf_exceptions.verapdf_parse_error_exception import VeraPdfParseErrorException
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf import verapdf_runner


def _normalize_violations(violations: list[VeraPdfViolation]) -> list[tuple[str, str, str, str, str, str]]:
    """Normalize violations for deterministic, order-insensitive comparison."""
    return sorted(
        (
            v.rule_id,
            v.clause,
            v.test_number,
            v.description,
            v.context,
            v.message,
        )
        for v in violations
    )


def test_error_case_run_verapdf_pdf_path_is_no_string():
    """
    Tests that run_verapdf raises a TypeError when the pdf_path argument is not a string.
    Simple test for defensive check.
    """
    with pytest.raises(TypeError):
        verapdf_runner.run_verapdf(123)  # type: ignore

def test_error_case_run_verapdf_pdf_path_does_not_exist():
    """
    Tests that run_verapdf raises an InvalidPdfPathException 
    when the pdf_path argument does not point to an existing file.
    """
    pdf_path = "RANDOM_PATH_THAT_DOES_NOT_EXIST.pdf"
    with pytest.raises(InvalidPdfPathException):
        verapdf_runner.run_verapdf(pdf_path)

def test_error_case_run_verapdf_pdf_path_does_point_to_non_pdf_file():
    """
    Tests that run_verapdf raises an InvalidPdfPathException 
    when the pdf_path argument does point so an existing file but 
    that file does not have a .pdf extension.
    """
    pdf_path = SRC_MAIN_PATH / "test" / "resources" / "verapdf_runner" / "this_file_is_not_a_pdf_test_file.txt"
    path = Path(pdf_path)
    if not path.exists() or not path.is_file() :
        pytest.fail()
    with pytest.raises(InvalidPdfPathException):
        verapdf_runner.run_verapdf(str(pdf_path))


# Verifies orchestration: run call, parse call, and unchanged return value.
def test_normal_case_run_verapdf_calls_runner_and_parser_and_returns_parser_result(monkeypatch: pytest.MonkeyPatch):
    pdf_path = SRC_MAIN_PATH / "test" / "resources" / "verapdf_runner" / "smoke_broken_fixture.pdf"
    xml_output = "<report></report>"
    expected_violations = [object(), object()]

    run_mock = MagicMock(return_value=xml_output)
    parse_mock = MagicMock(return_value=expected_violations)
    monkeypatch.setattr(verapdf_runner, "_run_verapdf", run_mock)
    monkeypatch.setattr(verapdf_runner, "parse_report", parse_mock)

    result = verapdf_runner.run_verapdf(str(pdf_path))

    run_mock.assert_called_once_with(str(pdf_path), verapdf_runner.VERAPDF_FLAVOUR, None)
    parse_mock.assert_called_once_with(xml_output)
    assert result is expected_violations


# Verifies parser failures are propagated unchanged by run_verapdf.
def test_run_verapdf_propagates_parse_error_exception_from_parse_report(monkeypatch: pytest.MonkeyPatch):
    pdf_path = SRC_MAIN_PATH / "test" / "resources" / "verapdf_runner" / "smoke_broken_fixture.pdf"
    xml_output = "<report></report>"
    expected_error = VeraPdfParseErrorException()

    run_mock = MagicMock(return_value=xml_output)
    parse_mock = MagicMock(side_effect=expected_error)
    monkeypatch.setattr(verapdf_runner, "_run_verapdf", run_mock)
    monkeypatch.setattr(verapdf_runner, "parse_report", parse_mock)

    with pytest.raises(VeraPdfParseErrorException) as raised:
        verapdf_runner.run_verapdf(str(pdf_path))

    run_mock.assert_called_once_with(str(pdf_path), verapdf_runner.VERAPDF_FLAVOUR, None)
    assert raised.value is expected_error


# Simulates "verapdf not installed" by forcing shutil.which("verapdf") to None.
# This validates the guard in _run_verapdf without requiring a separate shell setup.
def test_run_verapdf_raises_when_verapdf_not_installed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    # Also hide a copy installed by `pdfaccessguru doctor --install` (present in CI).
    monkeypatch.setattr(verapdf_runner, "find_verapdf", lambda: None)

    with pytest.raises(VeraPdfNotInstalledException):
        verapdf_runner._run_verapdf("sample.pdf", verapdf_runner.VERAPDF_FLAVOUR)


@pytest.mark.integration
@pytest.mark.skipif(
    shutil.which("verapdf") is None,
    reason="verapdf CLI not installed; integration test requires real console execution.",
)
# Integration test against real CLI, real PDF, and hardcoded expected violations.
def test_run_verapdf_real_console_smoke():
    sample_pdf = PROJECT_ROOT / "src" / "test" / "resources" / "verapdf_runner" / "smoke_broken_fixture.pdf"
    assert sample_pdf.exists(), f"Missing test PDF: {sample_pdf}"

    violations = verapdf_runner.run_verapdf(str(sample_pdf))

    expected = [
        VeraPdfViolation(
            rule_id="7.18.1-2",
            clause="7.18.1",
            test_number="2",
            description="An annotation (except Widget annotations or hidden annotations, or those having rectangle outside the crop-box) shall have either Contents key or an Alt entry in the enclosing structure element",
            context="root/document[0]/pages[0](6 0 obj PDPage)/annots[0](9 0 obj PDLinkAnnot)",
            message="Link annotation whose hidden flag is not set and whose rectangle is not outside the crop-box has neither Contents key nor an Alt entry in the enclosing structure element",
        ),
        VeraPdfViolation(
            rule_id="7.3-1",
            clause="7.3",
            test_number="1",
            description="Figure tags shall include an alternative representation or replacement text that represents the contents marked with the Figure tag as noted in ISO 32000-1:2008, 14.7.2, Table 323",
            context="root/document[0]/StructTreeRoot[0](5 0 obj PDStructTreeRoot)/K[0](7 0 obj SEDocument Document)/K[2](14 0 obj SEFigure Figure)",
            message="Figure structure element neither has an alternate description nor a replacement text",
        ),
        VeraPdfViolation(
            rule_id="7.18.5-2",
            clause="7.18.5",
            test_number="2",
            description="Links shall contain an alternate description via their Contents key as described in ISO 32000-1:2008, 14.9.3",
            context="root/document[0]/pages[0](6 0 obj PDPage)/annots[0](9 0 obj PDLinkAnnot)",
            message="A link annotation does not include an alternate description in the Contents key",
        ),
        VeraPdfViolation(
            rule_id="7.21.4.1-1",
            clause="7.21.4.1",
            test_number="1",
            description="The font programs for all fonts used for rendering within a conforming file shall be embedded within that file, as defined in ISO 32000-1:2008, 9.9",
            context="root/document[0]/pages[0](6 0 obj PDPage)/contentStream[0](10 0 obj PDSemanticContentStream)/operators[11]/font[0](Helvetica)",
            message="The font program is not embedded",
        ),
        VeraPdfViolation(
            rule_id="7.18.3-1",
            clause="7.18.3",
            test_number="1",
            description="Every page on which there is an annotation shall contain in its page dictionary the key Tabs, and its value shall be S",
            context="root/document[0]/pages[0](6 0 obj PDPage)",
            message="A page with annotation(s) contains Tabs key with value null instead of S",
        ),
        VeraPdfViolation(
            rule_id="7.1-10",
            clause="7.1",
            test_number="10",
            description="The document catalog dictionary shall include a ViewerPreferences dictionary containing a DisplayDocTitle key, whose value shall be true",
            context="root",
            message="ViewerPreferences dictionary is not present in the document Catalog, or DisplayDocTitle key is set to false or is not present in the ViewerPreferences dictionary (ViewerPreferences = null, DisplayDocTitle = null)",
        ),
        VeraPdfViolation(
            rule_id="7.1-9",
            clause="7.1",
            test_number="9",
            description="The Metadata stream in the document's catalog dictionary shall contain a dc:title entry, where dc is the recommended prefix for the Dublin Core metadata schema as defined in the XMP specification, which clearly identifies the document",
            context="root/document[0]/metadata[0](3 0 obj PDMetadata)/XMPPackage[0]",
            message="Metadata stream does not contain dc:title",
        ),
        VeraPdfViolation(
            rule_id="7.2-34",
            clause="7.2",
            test_number="34",
            description="Natural language for text in page content shall be determined",
            context="root/document[0]/pages[0](6 0 obj PDPage)/contentStream[0](10 0 obj PDSemanticContentStream)/content[1]{mcid:0}/contentItem[0]{mcid:0}",
            message="Natural language for text in page content cannot be determined",
        ),
        VeraPdfViolation(
            rule_id="7.2-34",
            clause="7.2",
            test_number="34",
            description="Natural language for text in page content shall be determined",
            context="root/document[0]/pages[0](6 0 obj PDPage)/contentStream[0](10 0 obj PDSemanticContentStream)/content[2]{mcid:1}/contentItem[0]{mcid:1}",
            message="Natural language for text in page content cannot be determined",
        ),
        VeraPdfViolation(
            rule_id="7.2-34",
            clause="7.2",
            test_number="34",
            description="Natural language for text in page content shall be determined",
            context="root/document[0]/pages[0](6 0 obj PDPage)/contentStream[0](10 0 obj PDSemanticContentStream)/content[3]{mcid:2}/contentItem[1]{mcid:2}",
            message="Natural language for text in page content cannot be determined",
        ),
        VeraPdfViolation(
            rule_id="7.2-34",
            clause="7.2",
            test_number="34",
            description="Natural language for text in page content shall be determined",
            context="root/document[0]/pages[0](6 0 obj PDPage)/contentStream[0](10 0 obj PDSemanticContentStream)/content[4]{mcid:3}/contentItem[0]{mcid:3}",
            message="Natural language for text in page content cannot be determined",
        ),
    ]

    assert _normalize_violations(violations) == _normalize_violations(expected)
