from pikepdf import Pdf
from threading import Event

#Warning: do never reorder these imports, these import must happen before importing CORRECTOR_FUNCTIONS
import pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi
import pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li
import pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart
import pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj
import pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle
import pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher
import pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache
import pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig

from pdfaccessguru.exceptions.corrector_exceptions.no_corrector_implemented_exception import NoCorrectorImplementedException
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.LLM.client import LLMNotConfigured
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import CORRECTOR_FUNCTIONS, DISABLED_CORRECTORS, NOT_CORRECTED_ON_PURPOSE
from pdfaccessguru.pipeline.reporting.scopes import report_correction
from pdfaccessguru.pipeline.reporting.writer import report_error, report_info, report_warn
from pdfaccessguru.utils.describers import describe_pikepdf_element


def correct(detected_violations: list[DetectedViolation], pdf: Pdf, cancel_event: Event | None = None,
) -> int:
    """
    Main function of PDFAccessGuruCorrect. Runs the pipeline step 'Correction'.
    Thus it corrects syntax, semantic and layout violations in the given PDF file.

    Parameters:
        - detected_violations (list[DetectedViolation]): List of detected violations to be corrected.
        - pdf (Pdf): The pikepdf PDF file to correct. Needed in case of affected element and
        supplementary_information is not sufficient.

    Modifies the PDF in place. Returns how many correctors actually ran (switched-off and
    missing correctors are not counted), so the caller knows whether a re-check is needed.
    """
    attempts = 0
    for detected_violation in detected_violations:
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Pipeline cancelled")
        try :
            with report_correction(detected_violation):
                if apply_correction(detected_violation, pdf):
                    attempts += 1
        except NoCorrectorImplementedException:
            report_info(f"No automatic fix exists yet for {detected_violation.violation.name}.")
    return attempts


def apply_correction(detected_violation: DetectedViolation, pdf: Pdf) -> bool:
    """
    Applies the correction for a single detected violation.

    Parameters:
        - detected_violation : The detected violation to correct.
        - pdf : The pikepdf PDF file to correct.
    Raises:
        - NoCorrectorImplementedException: If the corrector for the provided 
            violation is not implemented.
    """
    violation: Violation = detected_violation.violation

    disabled_reason = DISABLED_CORRECTORS.get(violation.name)
    if disabled_reason is not None:
        report_info(f"{NOT_CORRECTED_ON_PURPOSE}: the automatic fix for {violation.name} {disabled_reason}.")
        return False

    corrector = CORRECTOR_FUNCTIONS.get(violation.name)

    if corrector is not None:
        try:
            corrector(detected_violation, pdf)
            return True
        except LLMNotConfigured:
            report_info(f"The automatic fix for {violation.name} needs an AI model, which is not set up; "
                        "the problem stays open.")
        except CouldNotCorrectDetectedViolationException as exception:
            report_warn("Manual raise of CouldNotCorrectDetectedViolationException in corrector identified by the name"
                 f"{violation.name} running on the element {describe_pikepdf_element(detected_violation.affected_element)}: '{exception}'")
        except Exception as exception:
            report_error(f"Unexpected exception while correcting the DetectedViolation with name {violation.name} on the element described by '{describe_pikepdf_element(detected_violation.affected_element)}': '{exception}'")
        return True  # the corrector ran (and may have changed the file before failing)
    else:
        raise NoCorrectorImplementedException(violation.name)