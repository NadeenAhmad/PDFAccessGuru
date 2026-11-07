import pikepdf

from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.registry import (
    collect_supplementary_information_7_21_4_1_1,
)
from test.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.test_utils import (
    generate_resource_path,
)

def test_collect_supplementary_information_7_21_4_1_1_ProfPDFs():
    """
    Testet den Collector für Regel 7.21.4.1-1.

    Die PDF 7.21.4.1-t01-fail-a.pdf enthält eine nicht eingebettete Schriftart,
    die mit bestimmten Codes verwendet wird.

    Der Collector extrahiert nun direkt das Font-Objekt und die Codes
    des ersten Fonts auf der Seite.
    """
    violation = VeraPdfViolation(
        rule_id="7.21.4.1-1",
        clause="7.21.4.1",
        test_number="1",
        description="dummy description",
        context=(
            "root/document[0]/pages[1](36 0 obj PDPage)"
            "/contentStream[0](37 0 obj PDSemanticContentStream)/operators[294]/font[0](Arial-BoldMT)"
        ),
        message="dummy message",
    )

    pdf_path = generate_resource_path(
        "ProfPDFs/17052023_policy_paper_enefg_chancen_fuer_die_rechenzentrums_und_it-branche.pdf"
    )

    with pikepdf.open(pdf_path) as pdf:
        page = pdf.pages[1].obj

        result = collect_supplementary_information_7_21_4_1_1(
            violation,
            pdf,
            page,
        )

        # Der Collector gibt jetzt eine Liste mit genau zwei Elementen zurück
        # (Font-Objekt und used_codes) oder eine leere Liste.
        assert len(result) == 2, "Es wurde genau ein Font erwartet"

        font_obj, codes = result

        assert font_obj is not None, "Font-Objekt darf nicht None sein"

        # Die erwarteten Codes (aus der tatsächlichen PDF)
        expected_codes = [32]
        print("expected codes ", expected_codes)
        print("actual codes ", codes)
        # Sortierte Listen vergleichen (Reihenfolge egal)
        assert sorted(codes) == sorted(expected_codes), (
            f"Codes stimmen nicht überein: {sorted(codes)} != {sorted(expected_codes)}"
        )