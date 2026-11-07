import os
from pathlib import Path
from typing import Callable, Optional, List

import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.model.supplementary_information.supplementary_information import SupplementaryInformation




def _test_root() -> Path:
    return Path(__file__).resolve().parents[5]


def generate_resource_path(path: str) -> str:
    return str(_test_root() / "resources" / path)


def generate_test_result_path(path: str) -> str:
    return str(_test_root() / "test_results" / path)

def run_generic_corrector_debug_test(
    test_pdf_file: str,
    corrector: Callable[[DetectedViolation, pikepdf.Pdf], None],
    affected_element_detector: Callable[[pikepdf.Pdf], pikepdf.Object],
    supplementary_information_extractor: Callable[
        [pikepdf.Pdf],
        list[SupplementaryInformation]
    ],
) -> None:
    """
    Opens an already corrected PDF and runs the corrector only for debugging.

    No veraPDF validation is performed.
    """

    violation = Violation(
        category=ViolationCategory.SYNTAX,
        name="debug-notdef-glyph",
        description="Debug run on corrected PDF",
        guidelines=[],
    )

    pdf_path = generate_resource_path(test_pdf_file)

    with pikepdf.open(pdf_path) as pdf:

        affected_element = affected_element_detector(pdf)

        supplementary_information = (
            supplementary_information_extractor(pdf)
        )

        detected_violation = DetectedViolation(
            violation=violation,
            affected_element=affected_element,
            supplementary_information=supplementary_information,
        )

        corrector(
            detected_violation,
            pdf
        )