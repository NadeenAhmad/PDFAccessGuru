from .common import (
    CouldNotCorrectDetectedViolationException,
    DetectedViolation,
    Dictionary,
    Name,
    Pdf,
    _get_annotation_structure_context,
    corrector,
    pikepdf,
)


@corrector("widget-annotation-artifact-nested-tag-form")
def correct_widget_annotation_artifact_nested_tag_form(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.18.4-1

    Violation description:
    A Widget annotation is an Artifact or is not nested within a /Form tag.

    Correction strategy:
    The affected element is the widget annotation dictionary. To repair the
    failing case deterministically, locate the OBJR(object reference) entry in the logical
    structure tree that references this annotation, wrap that OBJR in a new
    /Form structure element, and register the new /Form element in the
    ParentTree under a fresh /StructParent key.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("widget-annotation-artifact-nested-tag-form")

    annotation_structure_context = _get_annotation_structure_context(
        detected_violation,
        "widget-annotation-artifact-nested-tag-form",
    )

    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    parent_tree = struct_tree_root.get("/ParentTree") if isinstance(struct_tree_root, pikepdf.Dictionary) else None
    nums = parent_tree.get("/Nums") if isinstance(parent_tree, pikepdf.Dictionary) else None

    if not isinstance(struct_tree_root, pikepdf.Dictionary) or \
            not isinstance(parent_tree, pikepdf.Dictionary) or \
            not isinstance(nums, pikepdf.Array):
        raise CouldNotCorrectDetectedViolationException("widget-annotation-artifact-nested-tag-form")

    parent_struct_elem = annotation_structure_context.objr_parent
    child_index = annotation_structure_context.objr_index
    objr_dict = annotation_structure_context.objr_dict

    if parent_struct_elem.get("/S") == Name("/Form"):
        return

    next_key = int(struct_tree_root.get("/ParentTreeNextKey", 0))
    page = affected_element.get("/P")

    if page is not None:
        objr_dict["/Pg"] = page

    form_struct_elem = pdf.make_indirect(Dictionary({
        "/Type": Name("/StructElem"),
        "/S": Name("/Form"),
        "/P": parent_struct_elem,
        "/K": objr_dict,
    }))

    kids = parent_struct_elem.get("/K")
    if isinstance(kids, pikepdf.Array):
        if child_index is None:
            raise CouldNotCorrectDetectedViolationException("widget-annotation-artifact-nested-tag-form")
        kids[child_index] = form_struct_elem
    elif isinstance(kids, pikepdf.Dictionary):
        parent_struct_elem["/K"] = form_struct_elem
    else:
        raise CouldNotCorrectDetectedViolationException("widget-annotation-artifact-nested-tag-form")

    affected_element["/StructParent"] = next_key
    nums.append(next_key)
    nums.append(form_struct_elem)
    struct_tree_root["/ParentTreeNextKey"] = next_key + 1
