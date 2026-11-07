from pathlib import Path

import pikepdf
from pikepdf import Object

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache import (
    correct_link_annotation_artifact_not_nested_tag_link,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collect_supplementary_information import (
    collect_supplementary_information,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_7_marwa_ayache.utils import (
    assert_verapdf_violation_removed,
    build_detected_syntax_violation,
    build_verapdf_violation,
    generate_resource_path,
    generate_test_output_path,
)


def test_correct_link_annotation_artifact_not_nested_tag_link(tmp_path: Path):
    """
    corrector test for rule 7.18.5-1.

    The affected element is the link annotation dictionary in the page's
    /Annots array. After correction, veraPDF should no longer report that the
    link annotation is not nested within a /Link tag.
    """
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.5-t01-fail-a.pdf")
    context_path = "root/document[0]/pages[0](27 0 obj PDPage)/annots[0](22 0 obj PDLinkAnnot)"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj.get("/Annots")[0]  # type: ignore[index]
        supplementary_information = collect_supplementary_information(
            build_verapdf_violation("7.18.5-1", context_path),
            pdf,
            affected_element,
        )
        detected_violation = build_detected_syntax_violation(
            "link-annotation-artifact-not-nested-tag-link",
            affected_element,
            supplementary_information,
        )

        correct_link_annotation_artifact_not_nested_tag_link(detected_violation, pdf)

        result_path = generate_test_output_path("7.18.5-1-corrected.pdf")
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.18.5-1", context_path)


def test_correct_link_annotation_with_nested_parent_tree(tmp_path: Path):
    """Correct an annotation whose ParentTree stores /Nums below /Kids."""
    pdf_path = generate_resource_path("veraPDF_corpus/7.18.5-t01-fail-a.pdf")
    context_path = "root/document[0]/pages[0](27 0 obj PDPage)/annots[0](22 0 obj PDLinkAnnot)"

    with pikepdf.open(pdf_path) as pdf:
        affected_element: Object = pdf.pages[0].obj.get("/Annots")[0]  # type: ignore[index]
        assert isinstance(affected_element, pikepdf.Dictionary)
        struct_parent = affected_element.get("/StructParent")
        assert struct_parent is not None
        struct_parent_key = int(str(struct_parent))
        struct_tree_root = pdf.Root.get("/StructTreeRoot")
        assert isinstance(struct_tree_root, pikepdf.Dictionary)
        parent_tree = struct_tree_root.get("/ParentTree")
        assert isinstance(parent_tree, pikepdf.Dictionary)
        nums = parent_tree.get("/Nums")
        assert isinstance(nums, pikepdf.Array)

        nested_nums = pikepdf.Array(list(nums))
        leaf = pdf.make_indirect(pikepdf.Dictionary({
            "/Limits": pikepdf.Array([int(str(nums[0])), int(str(nums[-2]))]),
            "/Nums": nested_nums,
        }))
        struct_tree_root["/ParentTree"] = pdf.make_indirect(pikepdf.Dictionary({
            "/Kids": pikepdf.Array([leaf]),
        }))

        supplementary_information = collect_supplementary_information(
            build_verapdf_violation("7.18.5-1", context_path),
            pdf,
            affected_element,
        )
        detected_violation = build_detected_syntax_violation(
            "link-annotation-artifact-not-nested-tag-link",
            affected_element,
            supplementary_information,
        )

        correct_link_annotation_artifact_not_nested_tag_link(detected_violation, pdf)

        corrected_struct_parent = affected_element.get("/StructParent")
        assert corrected_struct_parent is not None
        assert int(str(corrected_struct_parent)) == struct_parent_key
        corrected_parent = next(
            nested_nums[index + 1]
            for index in range(0, len(nested_nums), 2)
            if int(str(nested_nums[index])) == struct_parent_key
        )
        assert isinstance(corrected_parent, pikepdf.Dictionary)
        assert corrected_parent.get("/S") == pikepdf.Name("/Link")
        corrected_parent_tree = struct_tree_root.get("/ParentTree")
        assert isinstance(corrected_parent_tree, pikepdf.Dictionary)
        assert "/Nums" not in corrected_parent_tree

        result_path = tmp_path / "7.18.5-1-nested-parent-tree-corrected.pdf"
        pdf.save(result_path)

    assert_verapdf_violation_removed(str(result_path), "7.18.5-1", context_path)
