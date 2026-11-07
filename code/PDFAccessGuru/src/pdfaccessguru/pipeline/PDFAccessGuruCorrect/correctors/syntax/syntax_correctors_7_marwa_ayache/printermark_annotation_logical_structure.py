from .common import (
    CouldNotCorrectDetectedViolationException,
    DetectedViolation,
    Pdf,
    _get_annotation_structure_context,
    corrector,
    pikepdf,
)


@corrector("printermark-annotation-logical-structure")
def correct_printermark_annotation_logical_structure(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.18.8-1

    Violation description:
    A PrinterMark annotation is included in the logical structure.

    Correction strategy:
    PrinterMark annotations should not be connected to the logical structure
    tree. Remove the annotation's /StructParent link, delete the matching
    ParentTree entry, and remove the OBJR object that references the
    PrinterMark annotation from the structure tree.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException("printermark-annotation-logical-structure")

    annotation_structure_context = _get_annotation_structure_context(
        detected_violation,
        "printermark-annotation-logical-structure",
    )

    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    parent_tree = struct_tree_root.get("/ParentTree") if isinstance(struct_tree_root, pikepdf.Dictionary) else None
    nums = parent_tree.get("/Nums") if isinstance(parent_tree, pikepdf.Dictionary) else None

    if not isinstance(struct_tree_root, pikepdf.Dictionary) or \
            not isinstance(parent_tree, pikepdf.Dictionary) or \
            not isinstance(nums, pikepdf.Array):
        raise CouldNotCorrectDetectedViolationException("printermark-annotation-logical-structure")

    parent_struct_elem = annotation_structure_context.objr_parent
    child_index = annotation_structure_context.objr_index

    struct_parent_key = affected_element.get("/StructParent")
    if struct_parent_key is not None:
        for index in range(0, len(nums), 2):
            if int(nums[index]) == int(struct_parent_key):
                del nums[index + 1]
                del nums[index]
                break
        del affected_element["/StructParent"]

    parent_kids = parent_struct_elem.get("/K")
    if isinstance(parent_kids, pikepdf.Array) and child_index is not None:
        del parent_kids[child_index]
    elif isinstance(parent_kids, pikepdf.Dictionary):
        del parent_struct_elem["/K"]
    else:
        raise CouldNotCorrectDetectedViolationException("printermark-annotation-logical-structure")

    remaining_kids = parent_struct_elem.get("/K")
    if remaining_kids is None or (isinstance(remaining_kids, pikepdf.Array) and len(remaining_kids) == 0):
        grandparent_struct_elem = annotation_structure_context.objr_parent_parent
        parent_index = annotation_structure_context.objr_parent_parent_index
        if grandparent_struct_elem is not None:
            grandparent_kids = grandparent_struct_elem.get("/K")
            if isinstance(grandparent_kids, pikepdf.Array) and parent_index is not None:
                del grandparent_kids[parent_index]
            elif isinstance(grandparent_kids, pikepdf.Dictionary):
                del grandparent_struct_elem["/K"]
