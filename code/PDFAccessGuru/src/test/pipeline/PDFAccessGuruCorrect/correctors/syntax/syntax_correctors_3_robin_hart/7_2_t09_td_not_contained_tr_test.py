import importlib
import json
from unittest.mock import patch

import pikepdf
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart import (
    correct_td_not_contained_tr,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.detect import detect
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    generate_resource_path,
    generate_test_result_path,
)

corrector_module = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart.7_2_t09_td_not_contained_tr"
)

MOCK_SEND_PROMPT_RESPONSE = {
    "create_new_tr": "true"
}


@patch.object(corrector_module, "send_prompt", return_value=MOCK_SEND_PROMPT_RESPONSE)
def test_correct_td_not_contained_tr(mock_send_prompt):
    """
    Notes for detection: 
    resolve_context is not sufficient; the parent element of the resolved
    element is the affected element.
    """

    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t09-fail-a.pdf")
    test_result_path = generate_test_result_path("veraPDF_corpus/7.2-t09-fail-a_corrected.pdf")
    with pikepdf.open(pdf_path) as pdf:
        all_detected_violations = detect(pdf_path, pdf)
        detected_violations = [v for v in all_detected_violations if v.violation.name == "td-not-contained-tr"]

        for detected_violation in detected_violations:
            if detected_violation.affected_element == pdf.Root.get("/StructTreeRoot").get("/K").get("/K").get("/K")[1].get("/K")[0]: #type: ignore
                correct_td_not_contained_tr(detected_violation, pdf)
                break

        pdf.save(test_result_path)
    
    with pikepdf.open(test_result_path) as corrected_pdf:
        not_corrected_violations = detect(test_result_path, corrected_pdf)
        remaining_td_not_contained_tr = [
            v for v in not_corrected_violations if v.violation.name == "td-not-contained-tr"
        ]
        assert len(remaining_td_not_contained_tr) <= 1


MOCK_SEND_PROMPT_RESPONSE_2 = {
    "create_new_tr": "false",
    "id_of_tr_element": 6,
    "index_tr_elements_children": 1,
}

@patch.object(corrector_module, "send_prompt", return_value=MOCK_SEND_PROMPT_RESPONSE_2)
def test_correct_td_not_contained_tr_partially_corrected(mock_send_prompt):
    """
    Notes for detection: 
    resolve_context is not sufficient; the parent element of the resolved
    element is the affected element.
    """

    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t09-fail-b.pdf")
    test_result_path = generate_test_result_path("PDFAccessGuru_corpus/7.2-t09-fail-b_corrected.pdf")

    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        all_detected_violations = detect(pdf_path, pdf)
        detected_violations = [v for v in all_detected_violations if v.violation.name == "td-not-contained-tr"]

        correct_td_not_contained_tr(detected_violations[0], pdf)

        pdf.save(test_result_path)
    
    with pikepdf.open(test_result_path) as corrected_pdf:
        not_corrected_violations = detect(test_result_path, corrected_pdf)
        assert len(not_corrected_violations) <= 0


