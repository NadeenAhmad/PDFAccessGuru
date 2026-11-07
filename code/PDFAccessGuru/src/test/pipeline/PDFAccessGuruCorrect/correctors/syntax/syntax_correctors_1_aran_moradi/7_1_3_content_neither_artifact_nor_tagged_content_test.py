import pikepdf
from pikepdf import Name

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi import (
    correct_content_neither_artifact_nor_tagged_content,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    generate_resource_path,
)

TEXT_SHOWING = {"Tj", "TJ", "'", '"'}
PATH_PAINTING = {"S", "s", "f", "F", "f*", "B", "B*", "b", "b*"}


def _classify(page) -> dict[str, int]:
    """Count text and path painting operators inside and outside /Artifact sequences."""
    counts = {"text_in_artifact": 0, "text_untagged": 0, "path_in_artifact": 0, "path_untagged": 0}
    stack: list[str] = []
    for operands, operator in pikepdf.parse_content_stream(page):
        name = str(operator)
        if name in ("BDC", "BMC"):
            stack.append(str(operands[0]) if operands else "")
        elif name == "EMC":
            if stack:
                stack.pop()
        elif name in TEXT_SHOWING or name in PATH_PAINTING:
            kind = "text" if name in TEXT_SHOWING else "path"
            if "/Artifact" in stack:
                counts[f"{kind}_in_artifact"] += 1
            elif not stack:
                counts[f"{kind}_untagged"] += 1
    return counts


def _detected_violation(page) -> DetectedViolation:
    return DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name="content-neither-artifact-nor-tagged-content",
            description="",
            guidelines=[],
        ),
        affected_element=page,
        supplementary_information=[],
    )


def _untagged_page_pdf() -> pikepdf.Pdf:
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(200, 200))
    page = pdf.pages[0]
    page.obj["/Resources"] = pikepdf.Dictionary(
        Font=pikepdf.Dictionary(F1=pikepdf.Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica))
    )
    page.obj["/Contents"] = pdf.make_stream(
        b"0 0 0 RG 10 150 m 190 150 l S\n"        # decorative rule
        b"BT /F1 12 Tf 10 100 Td (Real text) Tj ET\n"  # real content
        b"0.9 g 10 10 180 20 re f\n"              # background box
    )
    return pdf


def test_7_1_3_marks_decoration_as_artifact_but_never_text():
    pdf = _untagged_page_pdf()
    page = pdf.pages[0]

    correct_content_neither_artifact_nor_tagged_content(_detected_violation(page), pdf)

    counts = _classify(page)
    assert counts["path_in_artifact"] == 2
    assert counts["path_untagged"] == 0
    assert counts["text_in_artifact"] == 0
    assert counts["text_untagged"] == 1


def test_7_1_3_does_not_hide_text_of_the_verapdf_fixture():
    with pikepdf.open(generate_resource_path("veraPDF_corpus/7.1-t03-fail-a.pdf")) as pdf:
        page = pdf.pages[0]
        before = _classify(page)

        correct_content_neither_artifact_nor_tagged_content(_detected_violation(page), pdf)

        after = _classify(page)
        assert after["text_in_artifact"] == before["text_in_artifact"]
        assert after["path_untagged"] == 0


def test_a_shared_form_drawn_inside_a_tag_gets_no_artifact_inside(tmp_path):
    """A form is drawn inside a tagged Figure on page 1 and untagged on page 2 (found in a real
    file). Marking its inside as an artifact for page 2 would put an artifact inside the Figure on
    page 1 (rule 7.1-2), so the form is left alone."""
    from collections import Counter

    from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf

    pdf = pikepdf.new()
    form = pdf.make_stream(b"0 0 0 RG 0 0 m 100 100 l S", Type=Name.XObject, Subtype=Name.Form,
                           BBox=[0, 0, 100, 100], Resources=pikepdf.Dictionary())
    for _ in range(2):
        pdf.add_blank_page(page_size=(200, 200))
    first, second = pdf.pages
    for page in (first, second):
        page.obj["/Resources"] = pikepdf.Dictionary(XObject=pikepdf.Dictionary(Fm0=form))
    first.obj["/Contents"] = pdf.make_stream(b"/Figure <</MCID 0>> BDC q 1 0 0 1 50 50 cm /Fm0 Do Q EMC")
    second.obj["/Contents"] = pdf.make_stream(b"q 1 0 0 1 50 50 cm /Fm0 Do Q")
    root = pdf.make_indirect(pikepdf.Dictionary(Type=Name.StructTreeRoot))
    document = pdf.make_indirect(pikepdf.Dictionary(Type=Name.StructElem, S=Name.Document, P=root))
    figure = pdf.make_indirect(pikepdf.Dictionary(Type=Name.StructElem, S=Name.Figure, P=document, Pg=first.obj,
                                                  K=0, Alt=pikepdf.String("A line")))
    document.K = pikepdf.Array([figure])
    root.K = pikepdf.Array([document])
    root.ParentTree = pdf.make_indirect(pikepdf.Dictionary(Nums=pikepdf.Array([0, pikepdf.Array([figure])])))
    root.ParentTreeNextKey = 1
    first.obj["/StructParents"] = 0
    pdf.Root.StructTreeRoot = root
    pdf.Root.MarkInfo = pikepdf.Dictionary(Marked=True)
    pdf.Root.Lang = pikepdf.String("en")

    correct_content_neither_artifact_nor_tagged_content(_detected_violation(second), pdf)

    assert b"Artifact" not in form.read_bytes()
    pdf.save(tmp_path / "out.pdf")
    assert Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))["7.1-2"] == 0
