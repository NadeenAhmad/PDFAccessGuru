from threading import Event

from pikepdf import Pdf
from sortedcontainers import SortedKeyList

from pdfaccessguru.exceptions.mapping_exceptions.could_not_find_affected_element_exception import CouldNotFindAffectedElementException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.map_violation import map_verapdf_violation_to_violation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.taxonomy_data_mapping.map_verapdf_violation_to_taxonomy_data import map_rule_id_to_syntax_violation_name
from pdfaccessguru.pipeline.reporting import report_debug
from pdfaccessguru.pipeline.reporting.scopes import report_mapping
from pdfaccessguru.pipeline.reporting.writer import report_warn, report_error

def detect(
    pdf_path: str, pdf: Pdf, cancel_event: Event | None = None
) -> list[DetectedViolation]:
    """
    Main function of PDFAccessGuruDetect. Runs the pipeline step 'Detection'.
    Thus it detects syntax, semantic and layout violations in the given PDF file.
    
    Requires that the pdf_path is valid.

    Arguments:
        pdf_path: The path to the PDF file.
        pdf: The PDF file as a pikepdf.PDF object.

    Returns: 
        A list of detected violations in the PDF file.
    """
    syntax_violations: list[DetectedViolation] = _detect_syntax_violations(
        pdf_path, pdf, cancel_event
    )

    #semantic_violations: list[Violation] = _detect_semantic_violations()
    #layout_violations: list[Violation] = _detect_layout_violations()

    detected_violations = syntax_violations
    return detected_violations


    
def _detect_syntax_violations(
    pdf_path: str, pdf: Pdf, cancel_event: Event | None = None
) -> list[DetectedViolation]:
    """
    Raises:
        VeraPdfNotInstalledException: If the veraPDF CLI is not installed
            or not available on the system PATH.
        VeraPdfWrongVersionException: If the installed veraPDF CLI version 
            is not version veraPDF 1.31 or higher
        VeraPDFProducedNoOutputException: If veraPDF runs but does not
            produce an XML report.
        VeraPdfParseErrorException: If the veraPDF XML report cannot be
            parsed into a valid XML tree.  

    """
    verapdf_violations: list[VeraPdfViolation] = run_verapdf(pdf_path, cancel_event)
    report_debug(f"Number of detected violations by veraPDF (total number of VeraPdfViolation objects in memory): {len(verapdf_violations)}")

    detected_violations = SortedKeyList(key=lambda x: (x.violation.rank, len(x.id), x.id))
    for verapdf_violation in verapdf_violations:
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Pipeline cancelled")
        with report_mapping(verapdf_violation):
            try:
                detected_violation: DetectedViolation = map_verapdf_violation_to_violation(
                    verapdf_violation, pdf
                )
                detected_violations.add(detected_violation)
            except CouldNotFindAffectedElementException as exception:
                report_warn(f"Manual raise of CouldNotFindAffectedElementException while mapping the violation {verapdf_violation.rule_id} with context {verapdf_violation.context} to a DetectedViolation: '{exception}'")
            except Exception as exception:
                report_error(f"Unexpected exception while mapping the violation {verapdf_violation.rule_id} with context {verapdf_violation.context} to a detected violation: '{exception}'")

    return list(detected_violations)


def violation_name(rule_id: str) -> str:
    """Taxonomy name of a veraPDF rule; rules without a corrector get 'unsupported-<rule id>'."""
    try:
        return map_rule_id_to_syntax_violation_name(rule_id)
    except KeyError:
        return f"unsupported-{rule_id}"


def map_violations(
    verapdf_violations: list[VeraPdfViolation], pdf: Pdf, cancel_event: Event | None = None
) -> list[DetectedViolation]:
    """
    Turn veraPDF findings into DetectedViolations (locate the PDF object, collect supporting
    information). Findings that cannot be located are reported and skipped here, but they stay
    in the counts, which are always taken from the veraPDF findings themselves.
    """
    detected: list[DetectedViolation] = []
    for verapdf_violation in verapdf_violations:
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Pipeline cancelled")
        with report_mapping(verapdf_violation):
            try:
                detected.append(map_verapdf_violation_to_violation(verapdf_violation, pdf))
            except CouldNotFindAffectedElementException as exception:
                report_warn(f"Could not locate the PDF object for {verapdf_violation.rule_id} at {verapdf_violation.context}: '{exception}'")
            except Exception as exception:
                report_error(f"Unexpected error while locating {verapdf_violation.rule_id} at {verapdf_violation.context}: '{exception}'")
    return detected


def _detect_semantic_violations() -> list[DetectedViolation]:
    # TODO: change signature: add correct parameters
    raise NotImplementedError("Semantic violation detection is not implemented yet.")
    return []

def _detect_layout_violations() -> list[DetectedViolation]:
    # TODO: change signature: add correct parameters
    raise NotImplementedError("Layout violation detection is not implemented yet.")
    return []


def rerun_detection(output_path: str, pdf: Pdf, cancel_event: Event | None = None) -> list[DetectedViolation]:
    """
    Runs the detection pipeline on tne provided output PDF file again.
    Used to provide verification that the correction was successful to the user.

    At the moment, just calls the detect function again.

    Arguments:
        output_path: The path to the output PDF file.
        pdf: The PDF file as a pikepdf.PDF object.

    Returns:
        A list of detected violations in the PDF file.
    """
    return detect(output_path, pdf, cancel_event)