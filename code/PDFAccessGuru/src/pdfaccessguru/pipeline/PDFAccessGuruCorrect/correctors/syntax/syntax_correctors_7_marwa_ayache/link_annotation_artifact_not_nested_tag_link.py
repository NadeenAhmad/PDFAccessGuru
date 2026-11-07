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


VIOLATION_NAME = "link-annotation-artifact-not-nested-tag-link"


@corrector("link-annotation-artifact-not-nested-tag-link")
def correct_link_annotation_artifact_not_nested_tag_link(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.18.5-1

    Violation description:
    A Link annotation is an Artifact or is not nested within a /Link tag.

    Correction strategy:
    The affected element is the link annotation dictionary. If an OBJR entry
    already references this annotation, wrap that OBJR in a new /Link structure
    element. If the document has a structure tree but the annotation has no OBJR
    yet, create a new /Link structure element with a new OBJR. In both cases,
    register the /Link element in the ParentTree under a fresh /StructParent key.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)

    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    parent_tree = struct_tree_root.get("/ParentTree") if isinstance(struct_tree_root, pikepdf.Dictionary) else None

    if not isinstance(struct_tree_root, pikepdf.Dictionary) or \
            not isinstance(parent_tree, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)

    try:
        annotation_structure_context = _get_annotation_structure_context(
            detected_violation,
            VIOLATION_NAME,
        )
    except CouldNotCorrectDetectedViolationException:
        _create_link_structure_for_unreferenced_annotation(
            pdf,
            affected_element,
            struct_tree_root,
            parent_tree,
        )
        return

    parent_struct_elem = annotation_structure_context.objr_parent
    child_index = annotation_structure_context.objr_index
    objr_dict = annotation_structure_context.objr_dict

    if parent_struct_elem.get("/S") == Name("/Link"):
        return

    page = affected_element.get("/P")

    if page is not None:
        objr_dict["/Pg"] = page

    link_struct_elem = pdf.make_indirect(Dictionary({
        "/Type": Name("/StructElem"),
        "/S": Name("/Link"),
        "/P": parent_struct_elem,
        "/K": pikepdf.Array([objr_dict]),
    }))

    if page is not None:
        link_struct_elem["/Pg"] = page

    kids = parent_struct_elem.get("/K")
    if isinstance(kids, pikepdf.Array):
        if child_index is None:
            raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)
        kids[child_index] = link_struct_elem
    elif isinstance(kids, pikepdf.Dictionary):
        parent_struct_elem["/K"] = link_struct_elem
    else:
        raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)

    struct_parent_key = affected_element.get("/StructParent")
    entry_location = (
        _find_number_tree_entry(parent_tree, int(struct_parent_key))
        if struct_parent_key is not None
        else None
    )

    if entry_location is not None:
        nums, value_index = entry_location
        nums[value_index] = link_struct_elem
        return

    next_key = _next_parent_tree_key(struct_tree_root, parent_tree)
    affected_element["/StructParent"] = next_key
    _insert_number_tree_entry(parent_tree, next_key, link_struct_elem)
    struct_tree_root["/ParentTreeNextKey"] = next_key + 1


def _create_link_structure_for_unreferenced_annotation(
    pdf: Pdf,
    annotation: pikepdf.Dictionary,
    struct_tree_root: pikepdf.Dictionary,
    parent_tree: pikepdf.Dictionary,
) -> None:
    """
    Create a /Link structure element for an annotation with no existing OBJR.

    This handles tagged PDFs where a structure tree already exists, but the link
    annotation is not represented in that tree yet.
    """
    parent_struct_elem = _select_structure_parent(struct_tree_root)
    next_key = _next_parent_tree_key(struct_tree_root, parent_tree)
    page = annotation.get("/P") or _find_page_for_annotation(pdf, annotation)

    objr_dict = Dictionary({
        "/Type": Name("/OBJR"),
        "/Obj": annotation,
    })
    if page is not None:
        objr_dict["/Pg"] = page

    link_struct_elem = pdf.make_indirect(Dictionary({
        "/Type": Name("/StructElem"),
        "/S": Name("/Link"),
        "/P": parent_struct_elem,
        "/K": pikepdf.Array([objr_dict]),
    }))
    if page is not None:
        link_struct_elem["/Pg"] = page

    _append_structure_child(parent_struct_elem, link_struct_elem)
    annotation["/StructParent"] = next_key
    _insert_number_tree_entry(parent_tree, next_key, link_struct_elem)
    struct_tree_root["/ParentTreeNextKey"] = next_key + 1


def _select_structure_parent(struct_tree_root: pikepdf.Dictionary) -> pikepdf.Dictionary:
    """Choose the structure element that should receive the new /Link child."""
    kids = struct_tree_root.get("/K")

    if isinstance(kids, pikepdf.Dictionary):
        return kids

    if isinstance(kids, pikepdf.Array):
        for child in kids:
            if isinstance(child, pikepdf.Dictionary):
                return child

    return struct_tree_root


def _append_structure_child(parent: pikepdf.Dictionary, child: pikepdf.Dictionary) -> None:
    """Append a child structure element while preserving existing /K entries."""
    kids = parent.get("/K")

    if kids is None:
        parent["/K"] = pikepdf.Array([child])
    elif isinstance(kids, pikepdf.Array):
        kids.append(child)
    elif isinstance(kids, (pikepdf.Dictionary, int)):
        parent["/K"] = pikepdf.Array([kids, child])
    else:
        raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)


def _find_number_tree_entry(
    number_tree: pikepdf.Dictionary,
    key: int,
) -> tuple[pikepdf.Array, int] | None:
    """Return the /Nums array and value index for a number-tree key."""
    nums = number_tree.get("/Nums")
    if isinstance(nums, pikepdf.Array):
        for index in range(0, len(nums), 2):
            if int(nums[index]) == key:
                return nums, index + 1

    kids = number_tree.get("/Kids")
    if isinstance(kids, pikepdf.Array):
        for kid in kids:
            if not isinstance(kid, pikepdf.Dictionary):
                continue
            result = _find_number_tree_entry(kid, key)
            if result is not None:
                return result

    return None


def _number_tree_keys(number_tree: pikepdf.Dictionary) -> list[int]:
    keys: list[int] = []
    nums = number_tree.get("/Nums")
    if isinstance(nums, pikepdf.Array):
        keys.extend(int(nums[index]) for index in range(0, len(nums), 2))

    kids = number_tree.get("/Kids")
    if isinstance(kids, pikepdf.Array):
        for kid in kids:
            if isinstance(kid, pikepdf.Dictionary):
                keys.extend(_number_tree_keys(kid))

    return keys


def _next_parent_tree_key(
    struct_tree_root: pikepdf.Dictionary,
    parent_tree: pikepdf.Dictionary,
) -> int:
    """Return a fresh ParentTree key for the new annotation structure entry."""
    next_key = int(struct_tree_root.get("/ParentTreeNextKey", 0))
    used_keys = _number_tree_keys(parent_tree)

    if used_keys:
        next_key = max(next_key, max(used_keys) + 1)

    return next_key


def _insert_number_tree_entry(
    number_tree: pikepdf.Dictionary,
    key: int,
    value: pikepdf.Object,
    *,
    is_root: bool = True,
) -> None:
    """Insert a key/value pair while preserving flat or nested number trees."""
    nums = number_tree.get("/Nums")
    if isinstance(nums, pikepdf.Array):
        pairs = [
            (int(nums[index]), nums[index + 1])
            for index in range(0, len(nums), 2)
        ]
        pairs.append((key, value))
        pairs.sort(key=lambda pair: pair[0])
        number_tree["/Nums"] = pikepdf.Array(
            [item for pair in pairs for item in pair]
        )
        _update_number_tree_limits(number_tree, is_root=is_root)
        return

    kids = number_tree.get("/Kids")
    if isinstance(kids, pikepdf.Array):
        child = _select_number_tree_child(kids, key)
        if child is None:
            child = pikepdf.Dictionary({"/Nums": pikepdf.Array()})
            kids.append(child)
        _insert_number_tree_entry(child, key, value, is_root=False)
        _update_number_tree_limits(number_tree, is_root=is_root)
        return

    number_tree["/Nums"] = pikepdf.Array([key, value])
    _update_number_tree_limits(number_tree, is_root=is_root)


def _select_number_tree_child(
    kids: pikepdf.Array,
    key: int,
) -> pikepdf.Dictionary | None:
    dictionary_kids = [kid for kid in kids if isinstance(kid, pikepdf.Dictionary)]
    for kid in dictionary_kids:
        limits = kid.get("/Limits")
        if isinstance(limits, pikepdf.Array) and len(limits) == 2:
            if key <= int(limits[1]):
                return kid
    return dictionary_kids[-1] if dictionary_kids else None


def _update_number_tree_limits(
    number_tree: pikepdf.Dictionary,
    *,
    is_root: bool,
) -> None:
    if is_root:
        return
    keys = _number_tree_keys(number_tree)
    if keys:
        number_tree["/Limits"] = pikepdf.Array([min(keys), max(keys)])


def _find_page_for_annotation(pdf: Pdf, annotation: pikepdf.Dictionary):
    """Find the page dictionary that contains the given annotation."""
    for page in pdf.pages:
        annots = page.obj.get("/Annots")
        if not isinstance(annots, pikepdf.Array):
            continue
        for candidate in annots:
            if candidate == annotation:
                return page.obj

    return None
