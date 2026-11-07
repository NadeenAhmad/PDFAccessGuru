import os
from pathlib import Path
from typing import Callable

import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.resolve_context import _parse_segments
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf


def generate_resource_path(path: str) -> str:
    """
    Generates the absolute path to a resource file in the test resources directory.
    """
    return str(Path(__file__).resolve().parents[5] / "resources" / path)

def generate_test_result_path(path: str) -> str:
    """
    Generates the absolute path to a cache file in the test cache directory.
    """
    return str(Path(__file__).resolve().parents[5] / "test_results" / path)

def have_equal_segment_parsing(context1: str, context2: str) -> bool:
    """
    Compares if the iteration over two context paths is the same.
    Context paths can differ in the content of (e.g.) brackets.
    Used for comparison of context paths in context of step function related tests.
    """
    generator1 = _parse_segments(context1)
    generator2 = _parse_segments(context2)

    for segment1, segment2 in zip(generator1, generator2):
        if segment1 != segment2:
            return False
    return True


def run_generic_syntax_test(
    violation_name: str,
    rule_id: str,
    test_pdf_file: str,
    corrector: Callable[[DetectedViolation, pikepdf.Pdf], None],
    context: str,
    traverse_pdf_function: Callable[[pikepdf.Pdf], pikepdf.Object]
):
    """
    Generic execution engine that opens a flawed PDF corpus file, isolates the 
    affected element, triggers the specified syntax corrector, and verifies that 
    veraPDF no longer reports the violation context.
    """
    violation = Violation(
        category=ViolationCategory.SYNTAX,
        name=violation_name,
        description="",
        guidelines=[]
    )
    
    pdf_path = generate_resource_path(f"veraPDF_corpus/{test_pdf_file}")
    corrected_file_name = f"{os.path.splitext(test_pdf_file)[0]}_corrected.pdf"
    result_path = generate_test_result_path(corrected_file_name)

    with pikepdf.open(pdf_path) as pdf:
        # Extract the node using the custom element path selector logic
        affected_element = traverse_pdf_function(pdf)

        detected_violation = DetectedViolation(
            violation=violation,
            affected_element=affected_element,
            supplementary_information=[]
        )

        # Execute correction
        corrector(detected_violation, pdf)
        pdf.save(result_path)

    # Validate utilizing veraPDF engine execution
    verapdf_violations = run_verapdf(result_path)

    for v_violation in verapdf_violations:
        assert v_violation.rule_id != rule_id or not have_equal_segment_parsing(
            v_violation.context, 
            context
        )
