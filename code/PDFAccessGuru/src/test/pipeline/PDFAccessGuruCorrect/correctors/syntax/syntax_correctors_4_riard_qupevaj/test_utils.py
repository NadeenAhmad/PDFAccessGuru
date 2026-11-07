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
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import (
    language_utils,
)
from pdfaccessguru.utils.compare_segment_parsing import have_equal_segment_parsing


def _test_root() -> Path:
    return Path(__file__).resolve().parents[5]


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
    violation = Violation(
        category=ViolationCategory.SYNTAX,
        name=map_rule_id_to_syntax_violation_name(rule_id),
        description="",
        guidelines=[],
    )

    pdf_path = generate_resource_path(test_pdf_file)
    corrected_file_name = f"{os.path.splitext(test_pdf_file)[0]}_corrected.pdf"
    result_path = generate_test_result_path(corrected_file_name)
    Path(result_path).parent.mkdir(parents=True, exist_ok=True)

    original_determine_lang_tag = language_utils.determine_lang_tag
    language_utils.determine_lang_tag = lambda text: "de-DE"
    try:
        with pikepdf.open(pdf_path) as pdf:
            detected_violation = DetectedViolation(
                violation=violation,
                affected_element=affected_element_detector(pdf),
                supplementary_information=[],
            )
            corrector(detected_violation, pdf)
            pdf.save(result_path)
    finally:
        language_utils.determine_lang_tag = original_determine_lang_tag

    verapdf_violations = run_verapdf(result_path)
    for verapdf_violation in verapdf_violations:
        assert verapdf_violation.rule_id != rule_id or not have_equal_segment_parsing(
            verapdf_violation.context,
            context,
        )
