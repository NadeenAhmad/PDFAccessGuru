import pikepdf


def find_objr_parent_for_annotation(current, annotation):
    """
    Find the structure element that directly contains an OBJR for the annotation.

    Returns:
        tuple(parent_struct_elem, child_index, objr_dict) if found, else None.
    """
    if not isinstance(current, pikepdf.Dictionary):
        return None

    kids = current.get("/K")
    if isinstance(kids, pikepdf.Dictionary):
        if kids.get("/Obj") == annotation:
            return current, None, kids
        return find_objr_parent_for_annotation(kids, annotation)

    if isinstance(kids, pikepdf.Array):
        for index, child in enumerate(kids):
            if not isinstance(child, pikepdf.Dictionary):
                continue
            if child.get("/Obj") == annotation:
                return current, index, child
            result = find_objr_parent_for_annotation(child, annotation)
            if result is not None:
                return result

    return None


def find_parent_of_struct_element(current, target):
    """
    Find the structure element that directly contains the given child element.

    Returns:
        tuple(parent_struct_elem, child_index) if found, else None.
    """
    if not isinstance(current, pikepdf.Dictionary):
        return None

    kids = current.get("/K")
    if isinstance(kids, pikepdf.Array):
        for index, child in enumerate(kids):
            if child == target:
                return current, index
            if isinstance(child, pikepdf.Dictionary):
                result = find_parent_of_struct_element(child, target)
                if result is not None:
                    return result
    elif isinstance(kids, pikepdf.Dictionary):
        if kids == target:
            return current, None
        return find_parent_of_struct_element(kids, target)

    return None
