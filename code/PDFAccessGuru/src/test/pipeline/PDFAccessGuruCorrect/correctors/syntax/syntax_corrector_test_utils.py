import os
from pathlib import Path
from typing import Callable

import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.taxonomy_data_mapping.map_verapdf_violation_to_taxonomy_data import (
    map_rule_id_to_syntax_violation_name,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from test.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.test_utils import (
    have_equal_segment_parsing,
)



def _test_root() -> Path:
    return Path(__file__).resolve().parents[4]


def generate_resource_path(path: str) -> str:
    return str(_test_root() / "resources" / path)


def generate_test_result_path(path: str) -> str:
    return str(_test_root() / "test_results" / path)


def run_generic_corrector_test(
    rule_id: str,
    test_pdf_file: str,
    corrector: Callable[[DetectedViolation, pikepdf.Pdf], None],
    context: str,
    affected_element_detector: Callable[[pikepdf.Pdf], pikepdf.Object],
) -> None:
    """
    Opens a violated PDF corpus file, isolates the affected element, runs the
    specified syntax corrector, and verifies that veraPDF no longer reports
    the violation at the given context path.

    **NOTE:**
    This Test does not test weather the corrector implementation introduced new violations 
    (at other context paths).

    Then stores the corrected PDF in the cache directory.

    Arguments:
        - rule_id: rule id of the violation to be corrected
        - test_pdf_file: pdf file path relative to src/test/resources/
        - corrector: method reference to corrector function to be tested
        - context: context path of the violation to be corrected
        - affected_element_detector: function to detect the affected element in the pdf
    """
    violation = Violation(
        category=ViolationCategory.SYNTAX,
        name=map_rule_id_to_syntax_violation_name(rule_id),
        description="",
        guidelines=[],
    )

    pdf_path = generate_resource_path(test_pdf_file)
    corrected_file_name = f"{os.path.splitext(test_pdf_file)[0]}_corrected.pdf"
    result_path = generate_test_result_path(corrected_file_name)

    with pikepdf.open(pdf_path) as pdf:
        affected_element = affected_element_detector(pdf)

        detected_violation = DetectedViolation(
            violation=violation,
            affected_element=affected_element,
            supplementary_information=[],
        )

        corrector(detected_violation, pdf)
        pdf.save(result_path)

    verapdf_violations = run_verapdf(result_path)

    for verapdf_violation in verapdf_violations:
        assert verapdf_violation.rule_id != rule_id or not have_equal_segment_parsing(
            verapdf_violation.context,
            context,
        )
