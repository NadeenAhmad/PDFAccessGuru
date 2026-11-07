from pathlib import Path
from typing import Callable, Optional

import pikepdf
import pytest

from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.resolve_context import _resolve_context
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.utils.cli_colors import CLIColors
from pdfaccessguru.utils.compare_segment_parsing import have_equal_segment_parsing
from pdfaccessguru.utils.describers import describe_pikepdf_element, describe_verapdf_violations


def generate_resource_path(path: str) -> str:
    """
    Helper method to generate the path to a resource file given its relative path.
    The resource files are located in src/test/resources/.
    Arguments:
        path: relative path of the resource file relative to src/test/resources/
    Returns:
        The absolute path to the resource file as a string.
    """
    return str(Path(__file__).resolve().parents[4] / "resources" / path)



def find_verapdf_violation(verapdf_violations: list[VeraPdfViolation], rule_id: str, context_path: str) -> VeraPdfViolation:
    """
    Finds deterministically the VeraPdfViolation with the given rule_id 
    and context_path in the list of verapdf_violations.

    Needed because the array of verapdf_violations returned by verapdf can be in any order, 
    so we cannot rely on the position of the violation in the array.

    Arguments:
        - verapdf_violations: list of VeraPdfViolation returned by verapdf for the given pdf file.
        - rule_id: The rule ID of the violation to find.
        - context_path: The context path of the violation to find.
    Returns:
        The VeraPdfViolation with the given rule_id and context_path.

    Will fail the test case if no such VeraPdfViolation is found in the list of verapdf_violations.
        
    """
    for violation in verapdf_violations:
        if violation.rule_id == rule_id and \
                    have_equal_segment_parsing(violation.context, context_path):
            return violation   
         
    pytest.fail(f"No violation with rule_id {rule_id} and context {context_path} found in the list of veraPDF violations. \
                    That means that verapdf did not detect any violation that is identified  \
                    by rule_id {rule_id} and context {context_path} by verapdf for the given pdf file. \
                    Maybe you specified the wrong file?")

def run_generic_resolve_context_test(
        pdf_path: str, 
        traverse_pdf_function: Callable[[pikepdf.Pdf], Optional[pikepdf.Object]],
        rule_id: str,
        context_path: str) -> None :
    """
    Runs a generic test for the _resolve_context function. 
    Is the basis for all test cases for _resolve_context, which only differ in the pdf file 
    used and the way to traverse to the expected element in the pdf.

    Asserts wether the element returned by _resolve_context is the same as the one returned 
    by the traverse_pdf_function. 
    Also fails if verapdf does not provide a VeraPdfViolation for the given rule_id and context_path.

    Arguments:
        - pdf_path: The path to the pdf file to be tested.
        - traverse_pdf_function: A function (lambda) that takes a pikepdf.Pdf object and traverses 
            it to the expected element (hardcoded for each test case by developer)
        - rule_id and context_path: needed to identify the correct VeraPdfViolation in the list 
            of violations returned by verapdf, which is the basis for the test.
    """

    verapdf_violations = run_verapdf(pdf_path)
    print(describe_verapdf_violations(verapdf_violations))

    with pikepdf.open(pdf_path) as pdf:
        expected = traverse_pdf_function(pdf)

        verapdf_violation = find_verapdf_violation(verapdf_violations, rule_id, context_path)
        actual = _resolve_context(verapdf_violation.context, pdf)
        if (actual != None and isinstance(actual, pikepdf.Object)) :
            print(f"{CLIColors.cyan("Found affected element description")}: {describe_pikepdf_element(actual)}")
            if expected is not None:
                print(f"{CLIColors.cyan("Will be compared to")}: {describe_pikepdf_element(expected)}")
            else:
                print(f"{CLIColors.cyan("Will be compared to")}: None")
        else :
            print(f"{CLIColors.cyan("No affected element was found, did return None")}")

        assert expected == actual
