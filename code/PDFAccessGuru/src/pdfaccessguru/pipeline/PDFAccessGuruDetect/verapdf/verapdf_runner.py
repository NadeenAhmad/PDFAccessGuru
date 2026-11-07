from pathlib import Path
import shutil
import subprocess
from threading import Event
import xml.etree.ElementTree as ET

from pdfaccessguru.exceptions.verapdf_exceptions.verapdf_not_installed_exception import VeraPdfNotInstalledException
from pdfaccessguru.exceptions.verapdf_exceptions.verapdf_produced_no_output_exception import VeraPDFProducedNoOutputException
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.exceptions.verapdf_exceptions.verapdf_parse_error_exception import VeraPdfParseErrorException
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.oscli.platform_prompt import PlatformPrompt
from pdfaccessguru.utils import verify_pdf_path
from pdfaccessguru.external_tools import find_verapdf, verapdf_environment


VERAPDF_FLAVOUR = "ua1"


def run_verapdf(
    pdf_path: str, cancel_event: Event | None = None
) -> list[VeraPdfViolation]:
    """
    Runs veraPDF on the given PDF file and returns all detected PDF/UA violations.

    This is the public entry point for veraPDF validation. It executes the
    veraPDF command-line tool with the configured PDF/UA flavour, reads the
    generated XML report, and converts all failed checks into VeraPdfViolation
    objects.

    Arguments:
        pdf_path: Path to the PDF file that should be validated.

    Returns:
        A list of VeraPdfViolation objects. The list is empty if veraPDF
        does not report any failed checks.

    Raises:
        VeraPdfNotInstalledException: If the veraPDF CLI is not installed
            or not available on the system PATH.
        VeraPdfWrongVersionException: If the installed veraPDF CLI version 
            is not version veraPDF 1.31 or higher
        VeraPDFProducedNoOutputException: If veraPDF runs but does not
            produce an XML report.
        VeraPdfParseErrorException: If the veraPDF XML report cannot be
            parsed into a valid XML tree.    
        TypeError: If the given pdf_path is not a string.
        InvalidPdfPathException: If the given pdf_path is invalid.
    """
    verify_pdf_path(pdf_path)

    xml_text: str = _run_verapdf(pdf_path, flavour_for(pdf_path), cancel_event)
    verapdf_violations: list[VeraPdfViolation] = parse_report(xml_text)
    return verapdf_violations
    

def flavour_for(pdf_path: str) -> str:
    """
    PDF/UA-1 applies to PDF 1.x files. A PDF 2.0 file is checked against PDF/UA-2 instead
    (rule 6.1-1 used to "fix" such files by relabelling them as PDF 1.7).
    """
    try:
        with open(pdf_path, "rb") as file:
            header = file.read(16)
    except OSError:
        return VERAPDF_FLAVOUR
    return "ua2" if header.startswith(b"%PDF-2.") else VERAPDF_FLAVOUR


def _run_verapdf(
    pdf_path: str, flavour: str = "ua1", cancel_event: Event | None = None
) -> str:
    """Run the verapdf CLI and return the raw XML report as a string."""
    verapdf = find_verapdf()
    if verapdf is None:
        raise VeraPdfNotInstalledException()

    absolut_path = Path.absolute(Path(pdf_path))
    command = [str(verapdf), "--flavour", flavour, "--format", "xml", "--maxfailuresdisplayed", "-1", str(absolut_path)]
    platform_prompt = PlatformPrompt()
    output = platform_prompt.execute(command, cancel_event=cancel_event, env=verapdf_environment())
    
    if not output:
        raise VeraPDFProducedNoOutputException()
    return output



def parse_report(xml_text: str) -> list[VeraPdfViolation]:
    """Extract every failed check from a veraPDF XML report."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as error:
        raise VeraPdfParseErrorException(error) from error

    violations: list[VeraPdfViolation] = []

    # Structure: report/jobs/job/validationReport/details/rule/check
    for rule in root.iter("rule"):
        if rule.attrib.get("status") != "failed":
            continue
        clause = rule.attrib.get("clause", "")
        test_no = rule.attrib.get("testNumber", "")
        description = (rule.findtext("description") or "").strip()

        for check in rule.findall("check"):
            if check.attrib.get("status") != "failed":
                continue
            context = (check.findtext("context") or "").strip()
            message = (check.findtext("errorMessage")
                       or check.findtext("message")
                       or "").strip()
            violations.append(VeraPdfViolation(
                rule_id=f"{clause}-{test_no}",
                clause=clause,
                test_number=test_no,
                description=description,
                context=context,
                message=message,
            ))
    return violations