import pikepdf
from pikepdf import Dictionary, Name, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.supplementary_information.supplementary_information import AnnotationStructureContextSupplementaryInformation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


def _replace_nth_occurrence(text: str, pattern: str, replacement: str, occurrence_index: int) -> str:
    """
    Replace the nth occurrence (0-based) of pattern in text.
    """
    start = 0
    for _ in range(occurrence_index + 1):
        match_index = text.find(pattern, start)
        if match_index == -1:
            return text
        start = match_index + len(pattern)

    return text[:match_index] + replacement + text[match_index + len(pattern):] #type:ignore


def _get_annotation_structure_context(
    detected_violation: DetectedViolation,
    violation_name: str,
) -> AnnotationStructureContextSupplementaryInformation:
    for supplementary_information in detected_violation.supplementary_information:
        if isinstance(supplementary_information, AnnotationStructureContextSupplementaryInformation):
            return supplementary_information

    raise CouldNotCorrectDetectedViolationException(violation_name)
