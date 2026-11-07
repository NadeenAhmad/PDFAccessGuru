
import importlib

from pdfaccessguru.model.supplementary_information.supplementary_information import (
    TableStructureContextSupplementaryInformation,
)
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart import prompt_determine_lang_tag
from pdfaccessguru.utils.cli_colors import CLIColors

_td_not_contained_tr_module = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart.7_2_t09_td_not_contained_tr"
)

def run_generic_prompt_determine_lang_tag_test(
    actual_text: str,
    expected_language_codes: list[str],
    iterations: int = 10,
    allowed_error_rate: float = 0.05,
) -> None:
    """
    Non-deterministic generic test for the prompt_determine_lang_tag function.
    The language code is determined by an LLM and may vary between runs, so this
    test can fail occasionally even when the prompt is adequate.
    Still, this test aims on testing whether the prompt is able to determine the language code of the actual text
    correctly at least a certain percentage of the time.

    The test prompts the prompt_determine_lang_tag function a specified number of times and 
    checks whether the returned language code is in the expected_language_codes list.

    WARNING: executing this generic test may drain our open-router credits.

    Arguments:
        actual_text: Text sample whose language the prompt should detect.
        expected_language_codes: Acceptable language tags for actual_text (subset of availableLocales.json).
        iterations: Number of prompt_determine_lang_tag calls to run.
        allowed_error_rate: Maximum fraction of iterations allowed to return
            a language code outside expected_language_codes (default 0.05).
            Test fails if actual error rate is greater than allowed_error_rate.
    """
    counter_correct_language_codes = 0
    print(f"Prompting determine_lang_tag {iterations} times...")
    for i in range(iterations):
        language_code = prompt_determine_lang_tag(actual_text)
        is_expected = language_code in expected_language_codes
        if is_expected:
            counter_correct_language_codes += 1
        message = f"Resulted language code in iteration {i}: {language_code}"
        print(CLIColors.green(message) if is_expected else CLIColors.color_fail(message))
    print("End prompting")

    success_rate = counter_correct_language_codes / iterations
    at_least_correct_quota = 1 - allowed_error_rate
    summary = (
        f"Correct language codes: {counter_correct_language_codes}/{iterations} "
        f"({success_rate * 100:.2f}%) — must reach at least {at_least_correct_quota * 100:.2f}%"
    )
    print(CLIColors.green(summary) if success_rate >= at_least_correct_quota else CLIColors.color_fail(summary))
    assert success_rate > at_least_correct_quota


_PLACEMENT_KEYS = frozenset({
    "id_of_parent_element",
    "index_parent_elements_children_for_new_tr",
    "id_of_tr_element",
    "index_tr_elements_children",
})


def _td_not_contained_tr_response_matches_expected(response: dict, expected: dict) -> bool:
    if response.get("create_new_tr") != expected["create_new_tr"]:
        return False

    if expected["create_new_tr"] == "true":
        return not _PLACEMENT_KEYS.intersection(response.keys())

    return (
        response.get("id_of_tr_element") == expected["id_of_tr_element"]
        and response.get("index_tr_elements_children") == expected["index_tr_elements_children"]
    )


def run_generic_prompt_td_not_contained_tr_test(
    test_data: dict,
    expected: dict,
) -> None:
    """
    Generic test for the td-not-contained-tr prompt.

    Sends the prompt once, prints the LLM response, and asserts it matches expected.

    WARNING: executing this generic test may drain our open-router credits.

    Arguments:
        test_data: Dict with table_json, id_to_bounding_box_mapping_json, and
            affected_element_id keys used to build the prompt.
        expected: Expected JSON response from the LLM.
    """
    supplementary_information = TableStructureContextSupplementaryInformation(
        table_json=test_data["table_json"],
        id_to_bounding_box_mapping_json=test_data["id_to_bounding_box_mapping_json"],
        id_to_table_elements_mapping={},
        table_element=None,  # type: ignore[arg-type]
        parent_of_affected_element=None,  # type: ignore[arg-type]
    )
    affected_element_id = test_data["affected_element_id"]

    print("Prompting td-not-contained-tr...")
    response = _td_not_contained_tr_module.send_prompt(
        supplementary_information,
        affected_element_id,
    )
    is_expected = _td_not_contained_tr_response_matches_expected(response, expected)
    message = f"LLM response: {response}"
    print(CLIColors.green(message) if is_expected else CLIColors.color_fail(message))
    print(f"Expected: {expected}")
    assert is_expected, f"LLM response {response} did not match expected {expected}"
