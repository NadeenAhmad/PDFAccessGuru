import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle import (
    correct_node_more_one_h_tag,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    generate_resource_path,
    run_generic_corrector_test,
)


def _detected_violation(node: pikepdf.Object) -> DetectedViolation:
    """Create the violation object expected by the corrector."""
    return DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name="node-more-one-h-tag",
            description="",
            guidelines=[],
        ),
        affected_element=node,
        supplementary_information=[],
    )


def _affected_node(pdf: pikepdf.Pdf) -> pikepdf.Dictionary:
    """Resolve the affected /Sect without optional chained accesses."""
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    assert isinstance(structure_tree_root, pikepdf.Dictionary)

    document = structure_tree_root.get("/K")
    assert isinstance(document, pikepdf.Dictionary)

    section = document.get("/K")
    assert isinstance(section, pikepdf.Dictionary)
    return section


def _structure(element) -> list[str]:
    kids = element.get("/K")
    kids = list(kids) if isinstance(kids, pikepdf.Array) else [kids]
    return [str(kid.get("/S")) for kid in kids if isinstance(kid, pikepdf.Dictionary)]


def test_correct_node_more_one_h_tag():
    run_generic_corrector_test(
        rule_id="7.4.4-1",
        test_pdf_file="veraPDF_corpus/7.4.4-t01-fail-a.pdf",
        corrector=correct_node_more_one_h_tag,
        context=(
            "root/document[0]/StructTreeRoot[0](10 0 obj PDStructTreeRoot)/K[0]"
            "(19 0 obj SEDocument Document)/K[0](25 0 obj SESect Sect)"
        ),
        affected_element_detector=_affected_node,
    )


def test_every_heading_stays_a_heading_and_gets_its_own_section():
    """Sect(H, P, H) becomes Sect(H, P), Sect(H): no heading is turned into a paragraph."""
    with pikepdf.open(generate_resource_path("veraPDF_corpus/7.4.4-t01-fail-a.pdf")) as pdf:
        section = _affected_node(pdf)
        document = section.get("/P")

        correct_node_more_one_h_tag(_detected_violation(section), pdf)

        assert _structure(document) == ["/Sect", "/Sect"]
        first, second = list(document.get("/K"))
        assert _structure(first) == ["/H", "/P"]
        assert _structure(second) == ["/H"]
        assert str(second.get("/P").get("/S")) == "/Document"


def test_a_node_with_one_heading_is_left_alone():
    pdf = pikepdf.Pdf.new()
    heading = pikepdf.Dictionary({"/S": pikepdf.Name("/H")})
    section = pdf.make_indirect(pikepdf.Dictionary({"/S": pikepdf.Name("/Sect"), "/K": heading}))

    correct_node_more_one_h_tag(_detected_violation(section), pdf)

    assert str(heading.get("/S")) == "/H"
    assert _structure(section) == ["/H"]


def test_custom_heading_tags_are_recognised_via_the_role_map():
    with pikepdf.open(generate_resource_path("veraPDF_corpus/7.4.4-t01-fail-a.pdf")) as pdf:
        structure_tree_root = pdf.Root.get("/StructTreeRoot")
        structure_tree_root["/RoleMap"] = pikepdf.Dictionary({"/CustomHeading": pikepdf.Name("/H")})
        section = _affected_node(pdf)
        children = section.get("/K")
        children[0]["/S"] = pikepdf.Name("/CustomHeading")
        children[2]["/S"] = pikepdf.Name("/CustomHeading")

        correct_node_more_one_h_tag(_detected_violation(section), pdf)

        document = section.get("/P")
        assert _structure(document) == ["/Sect", "/Sect"]
        assert [_structure(kid)[0] for kid in document.get("/K")] == ["/CustomHeading", "/CustomHeading"]
