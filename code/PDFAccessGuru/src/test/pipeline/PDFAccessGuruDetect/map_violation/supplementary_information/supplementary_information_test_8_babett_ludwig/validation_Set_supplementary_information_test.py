import pikepdf

from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.registry import (
    collect_supplementary_information_7_21_4_1_1,
)
from test.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.test_utils import (
    generate_resource_path,
)

def test_collect_supplementary_information_7_21_4_1_1_validation_Set():
    violation = VeraPdfViolation(
        rule_id="7.21.4.1-1",
        clause="7.21.4.1",
        test_number="1",
        description="dummy description",
        context=(
            "root/document[0]/pages[0](7 0 obj PDPage)"
            "/contentStream[0]/operators[434]/font[0](Times-Roman)"
        ),
        message="dummy message",
    )

    pdf_path = generate_resource_path(
        "validation_Set/functional_hyperlinks_FAILED_W2893185172_0.pdf"
    )

    with pikepdf.open(pdf_path) as pdf:
        page = pdf.pages[0].obj

        result = collect_supplementary_information_7_21_4_1_1(
            violation,
            pdf,
            page,
        )

       
        assert len(result) == 2, "Es wurde genau ein Font erwartet"

        font_obj, codes = result

        assert font_obj is not None, "Font-Objekt darf nicht None sein"
        
        expected_codes = [32, 45, 46, 48, 49, 50, 51, 55, 56, 57, 58, 83, 88, 91, 93, 97, 99, 101, 104, 105, 109, 112, 114, 115, 118, 121]
        print("expected codes ", expected_codes)
        print("actual codes ", codes)
        
        assert sorted(codes) == sorted(expected_codes), (
            f"Codes stimmen nicht überein: {sorted(codes)} != {sorted(expected_codes)}"
        )