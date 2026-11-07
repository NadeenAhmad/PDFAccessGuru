from pikepdf import Array, Dictionary, Name, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


def _get_structure_type(element):
    return element.get("/S") if hasattr(element, "get") else None


def _resolve_structure_type(structure_type, role_map: Dictionary | None):
    """Resolve custom structure types while protecting against RoleMap cycles."""
    if role_map is None:
        return structure_type

    current = structure_type
    visited: set[str] = set()
    while isinstance(current, Name):
        role_name = str(current)
        if role_name in visited or role_name not in role_map:
            break
        visited.add(role_name)
        mapped_role = role_map.get(role_name)
        if not isinstance(mapped_role, Name):
            break
        current = mapped_role
    return current


def _get_heading_level(element, role_map: Dictionary | None = None) -> int | None:
    structure_type = str(
        _resolve_structure_type(_get_structure_type(element), role_map)
    )
    if len(structure_type) == 3 and structure_type.startswith("/H"):
        level = structure_type[2]
        if level in "123456":
            return int(level)
    return None


def _collect_headings(
    element,
    headings: list,
    role_map: Dictionary | None = None,
) -> None:
    if not hasattr(element, "get"):
        return

    if _get_heading_level(element, role_map) is not None:
        headings.append(element)

    children = element.get("/K")
    if isinstance(children, Array):
        for child in children:
            _collect_headings(child, headings, role_map)
    else:
        _collect_headings(children, headings, role_map)


def _is_same_element(first, second) -> bool:
    if first is second:
        return True

    first_objgen = getattr(first, "objgen", None)
    second_objgen = getattr(second, "objgen", None)
    return first_objgen not in (None, (0, 0)) and first_objgen == second_objgen


@corrector("heading-level-skipped")
def correct_heading_level_skipped(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.4.2-1

    Violation description: Heading level is skipped in a descending sequence of header levels

    Correction strategy:
    --> Do it without LLM. Change H3 to H2, inclunding all following.
    Only change the heading level if there is a skip of the heading level.

    H1 --> H1
    ...
    H3 --> H2
    ...
    H3 --> H2
    ...
    H2 --> H2 (stays the same, beacuse no heading level is skipped)
    ...
    H3 --> H3 (stays the same, beacuse no heading level is skipped)

    """
    affected_element = detected_violation.affected_element
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    role_map = (
        structure_tree_root.get("/RoleMap")
        if isinstance(structure_tree_root, Dictionary)
        else None
    )
    if not isinstance(role_map, Dictionary):
        role_map = None

    if _get_heading_level(affected_element, role_map) is None:
        raise CouldNotCorrectDetectedViolationException(
            detected_violation.violation.name
        )

    headings = []
    _collect_headings(structure_tree_root, headings, role_map)

    affected_index = next(
        (
            index
            for index, heading in enumerate(headings)
            if _is_same_element(heading, affected_element)
        ),
        None,
    )
    if affected_index is None:
        raise CouldNotCorrectDetectedViolationException(
            detected_violation.violation.name
        )

    previous_level = 0
    if affected_index > 0:
        previous_level = (
            _get_heading_level(headings[affected_index - 1], role_map) or 0
        )

    for heading in headings[affected_index:]:
        heading_level = _get_heading_level(heading, role_map)
        if heading_level is None:
            continue

        maximum_next_level = previous_level + 1
        if heading_level > maximum_next_level:
            heading_level = maximum_next_level
            heading["/S"] = Name(f"/H{heading_level}")

        previous_level = heading_level
