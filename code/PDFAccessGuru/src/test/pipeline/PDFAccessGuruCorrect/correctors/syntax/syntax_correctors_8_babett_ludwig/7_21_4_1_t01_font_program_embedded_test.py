import os
from pathlib import Path
from typing import Callable

import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.model.supplementary_information.supplementary_information import SupplementaryInformation
from .run_generic_supplementary_information import (
    run_generic_supplementary_information_corrector_test,
)
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_font_program_embedded,
)

'''
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.taxonomy_data_mapping.map_verapdf_violation_to_taxonomy_data import (
    map_rule_id_to_syntax_violation_name,
)

from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf

from test.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.test_utils import (
    have_equal_segment_parsing,
)


def _test_root() -> Path:
    return Path(__file__).resolve().parents[5]


def generate_resource_path(path: str) -> str:
    return str(_test_root() / "resources" / path)


def generate_test_result_path(path: str) -> str:
    return str(_test_root() / "test_results" / path)


def run_generic_corrector_supplementary_information_test(
    rule_id: str,
    test_pdf_file: str,
    corrector: Callable[[DetectedViolation, pikepdf.Pdf], None],
    context: str,
    affected_element_detector: Callable[[pikepdf.Pdf], pikepdf.Object],
    supplementary_information_extractor: Callable[[pikepdf.Pdf], list[SupplementaryInformation]],
) -> None:
    """
    Extended version of the generic corrector test that supports supplementary information.
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
        supplementary_information = supplementary_information_extractor(pdf)

        detected_violation = DetectedViolation(
            violation=violation,
            affected_element=affected_element,
            supplementary_information=supplementary_information,
        )

        corrector(detected_violation, pdf)
        pdf.save(result_path)

    verapdf_violations = run_verapdf(result_path)

    for verapdf_violation in verapdf_violations:
        assert verapdf_violation.rule_id != rule_id or not have_equal_segment_parsing(
            verapdf_violation.context,
            context,
        )
'''

def test_correct_font_program_embedded():
    """
    Tests correction of missing embedded font programs (7.21.4.1-1).
    """

    def affected_element_detector(pdf):
        return pdf.pages[0].obj



    def supplementary_information_extractor(pdf):
        
        
        font = pdf.pages[0].obj["/Resources"]["/Font"]["/T1_0"]
        used_codes =  {32, 97, 101, 71, 103, 108, 111, 112, 115, 116}

        # Rückgabe als flache Liste: [Font-Objekt, used_codes]
        return [font, used_codes]



    run_generic_supplementary_information_corrector_test(
        rule_id="7.21.4.1-1",
        test_pdf_file="veraPDF_corpus/7.21.4.1-t01-fail-a.pdf",
        corrector=correct_font_program_embedded,
        context=(
            "root/document[0]/pages[0](27 0 obj PDPage)/contentStream[0]"
            "(28 0 obj PDSemanticContentStream)/operators[4]/font[0](Helvetica)"
        ),
        affected_element_detector=affected_element_detector,
        supplementary_information_extractor=supplementary_information_extractor,
    )