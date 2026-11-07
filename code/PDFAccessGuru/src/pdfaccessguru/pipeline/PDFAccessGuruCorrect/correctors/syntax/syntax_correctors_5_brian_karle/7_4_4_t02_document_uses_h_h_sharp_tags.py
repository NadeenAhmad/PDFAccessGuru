import json
from dataclasses import dataclass

from pikepdf import Dictionary, Name, Pdf

from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_review
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle.heading_context_utils import (
    TextContext,
    element_identity,
    element_text,
    extract_text_context,
    get_role_map,
    metadata_text,
    page_index_for_element,
    resolve_role,
    structure_children,
)


_MAX_STRUCTURE_NODES = 5000
_MAX_CONTEXT_LENGTH = 500000
_NUMBERED_HEADING_TAGS = frozenset(Name(f"/H{level}") for level in range(1, 7))


@dataclass
class _HeadingCandidate:
    """An unnumbered /H element that needs a numbered heading level."""

    candidate_id: str
    element: Dictionary
    document_index: int


@dataclass(frozen=True)
class _HeadingAssignment:
    """A validated LLM decision assigning one candidate to /H1 through /H6."""

    candidate_id: str
    level: int


@corrector("document-uses-h-h#-tags")
def correct_document_uses_h_h_sharp_tags(
    detected_violation: DetectedViolation,
    pdf: Pdf,
) -> None:
    """
    Correct veraPDF rule 7.4.4-2.

    A strongly structured document must use numbered headings consistently.
    Every unnumbered /H in the document is sent to the LLM together with the
    complete structure order and extracted MCID text. After strict validation,
    all candidates are changed to the selected /H1 through /H6 tags.
    """
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(structure_tree_root, Dictionary):
        raise _correction_error(detected_violation, "document has no structure tree")

    role_map = get_role_map(pdf)
    structure_elements = _collect_structure_elements(
        structure_tree_root, detected_violation
    )
    candidates = _collect_heading_candidates(structure_elements, role_map)
    numbered_headings = _collect_numbered_heading_levels(
        structure_elements, role_map
    )

    # A stale violation or a consistently weakly structured document needs no change.
    if not candidates or not numbered_headings:
        return

    # Extract readable content before asking the LLM for semantic heading levels.
    # Choosing the levels needs an AI; check that before reading the text of the whole document
    # (that reading took about 20 seconds per finding on large files, Phase 5).
    from pdfaccessguru.LLM.client import LLMNotConfigured
    from pdfaccessguru.LLM.fallback import ai_available
    if not ai_available():
        raise LLMNotConfigured("choosing heading levels needs an AI model")
    text_context = extract_text_context(pdf, detected_violation)
    context_json = _render_heading_context(
        structure_elements,
        candidates,
        role_map,
        text_context,
        detected_violation,
    )
    if len(context_json) > _MAX_CONTEXT_LENGTH:
        raise _correction_error(
            detected_violation, "structure context is too large for the LLM"
        )

    assignments = determine_numbered_heading_tags(context_json)
    assignments_by_id = _validate_assignments(
        assignments, candidates, detected_violation
    )
    _validate_final_heading_sequence(
        structure_elements,
        candidates,
        assignments_by_id,
        role_map,
        detected_violation,
    )

    # Apply all assignments only after the complete response has passed validation.
    for candidate in candidates:
        level = assignments_by_id[candidate.candidate_id]
        candidate.element["/S"] = Name(f"/H{level}")
        report_review(f"A heading level (H{level}) was chosen by a language model. Please check the heading structure.")


def determine_numbered_heading_tags(context_json: str) -> list[_HeadingAssignment]:
    """Ask the LLM to assign /H1 through /H6 to every unnumbered heading."""
    provider = OpenRouterBaseProvider()
    system_prompt, user_prompt = build_prompt_determine_numbered_heading_tags(
        context_json
    )
    response = provider.send_message(system_prompt, user_prompt, json_mode=True)

    try:
        parsed = json.loads(response)
        raw_assignments = parsed["heading_assignments"]
        if not isinstance(raw_assignments, list):
            raise TypeError("heading_assignments is not a list")

        assignments: list[_HeadingAssignment] = []
        for raw_assignment in raw_assignments:
            if not isinstance(raw_assignment, dict):
                raise TypeError("heading assignment is not an object")
            candidate_id = raw_assignment.get("id")
            level = raw_assignment.get("level")
            if (
                not isinstance(candidate_id, str)
                or isinstance(level, bool)
                or not isinstance(level, int)
            ):
                raise TypeError("heading assignment has invalid fields")
            assignments.append(_HeadingAssignment(candidate_id, level))
        return assignments
    except (json.JSONDecodeError, KeyError, TypeError) as exception:
        raise CouldNotCorrectDetectedViolationException(
            "document-uses-h-h#-tags: invalid LLM response"
        ) from exception


def build_prompt_determine_numbered_heading_tags(
    context_json: str,
) -> tuple[str, str]:
    """Build the prompt while keeping all PDF-derived content in the user role."""
    system_prompt = """You correct heading levels in a strongly structured PDF/UA document.
The document mixes numbered /H1 through /H6 tags with unnumbered /H tags. Assign a
numbered level from 1 to 6 to every candidate /H.

Use the complete document-order context: existing heading levels, hierarchy depth,
section titles, sibling order, and extracted marked-content text. Preserve a logical
outline. A deeper subsection normally has a greater level than its containing section,
and heading levels must not skip when descending (for example /H1 followed by /H3 is
invalid unless an /H2 occurs between them). Do not omit candidates or invent IDs.

Return only JSON in this exact form:
{"heading_assignments": [{"id": "candidate-h-1", "level": 2}]}"""
    user_prompt = f"PDF heading context:\n{context_json}"
    return system_prompt, user_prompt


def _collect_structure_elements(
    structure_tree_root: Dictionary,
    detected_violation: DetectedViolation,
) -> list[tuple[Dictionary, int, int | None]]:
    """Collect structure elements with their depth and parent list index."""
    elements: list[tuple[Dictionary, int, int | None]] = []
    visited: set[tuple[int, int] | int] = set()

    def visit(
        element: Dictionary,
        depth: int,
        parent_index: int | None,
    ) -> None:
        """Walk structure children in document order and reject oversized trees."""
        if len(elements) >= _MAX_STRUCTURE_NODES:
            raise _correction_error(detected_violation, "structure tree is too large")
        identity = element_identity(element)
        if identity in visited:
            return
        visited.add(identity)
        document_index = len(elements)
        elements.append((element, depth, parent_index))
        for child in structure_children(element):
            visit(child, depth + 1, document_index)

    for child in structure_children(structure_tree_root):
        visit(child, 0, None)
    return elements


def _collect_heading_candidates(
    structure_elements: list[tuple[Dictionary, int, int | None]],
    role_map: Dictionary | None,
) -> list[_HeadingCandidate]:
    """Collect every unnumbered /H in document order, including RoleMap aliases."""
    candidates: list[_HeadingCandidate] = []
    for document_index, (element, _, _) in enumerate(structure_elements):
        if resolve_role(element.get("/S"), role_map) == Name("/H"):
            candidates.append(
                _HeadingCandidate(
                    candidate_id=f"candidate-h-{len(candidates) + 1}",
                    element=element,
                    document_index=document_index,
                )
            )
    return candidates


def _collect_numbered_heading_levels(
    structure_elements: list[tuple[Dictionary, int, int | None]],
    role_map: Dictionary | None,
) -> list[int]:
    """Return the levels of all existing numbered headings in document order."""
    levels: list[int] = []
    for element, _, _ in structure_elements:
        level = _numbered_heading_level(resolve_role(element.get("/S"), role_map))
        if level is not None:
            levels.append(level)
    return levels


def _render_heading_context(
    structure_elements: list[tuple[Dictionary, int, int | None]],
    candidates: list[_HeadingCandidate],
    role_map: Dictionary | None,
    text_context: TextContext,
    detected_violation: DetectedViolation,
) -> str:
    """Serialize hierarchy, existing levels, candidates and extracted text for the LLM."""
    candidate_by_index = {
        candidate.document_index: candidate for candidate in candidates
    }
    page_indexes: list[int | None] = []
    nodes: list[dict] = []

    for document_index, (element, depth, parent_index) in enumerate(structure_elements):
        # Resolve /Pg against the actual parent rather than the preceding document node.
        inherited_page_index = (
            page_indexes[parent_index] if parent_index is not None else None
        )
        page_index = page_index_for_element(
            element,
            inherited_page_index,
            text_context.page_index_by_objgen,
        )
        page_indexes.append(page_index)
        candidate = candidate_by_index.get(document_index)
        resolved_role = resolve_role(element.get("/S"), role_map)
        nodes.append(
            {
                "id": candidate.candidate_id if candidate else f"node-{document_index + 1}",
                "tag": str(resolved_role),
                "original_tag": str(element.get("/S")),
                "depth": depth,
                "is_candidate": candidate is not None,
                "existing_heading_level": _numbered_heading_level(resolved_role),
                "title": metadata_text(element),
                "text": element_text(element, page_index, text_context),
            }
        )

    serializable = {
        "instruction": "Assign /H1 through /H6 to every unnumbered /H candidate.",
        "candidate_ids": [candidate.candidate_id for candidate in candidates],
        "structure_nodes_in_document_order": nodes,
    }
    result = json.dumps(serializable, ensure_ascii=False, separators=(",", ":"))
    if not nodes:
        raise _correction_error(detected_violation, "structure tree is empty")
    return result


def _validate_assignments(
    assignments: list[_HeadingAssignment],
    candidates: list[_HeadingCandidate],
    detected_violation: DetectedViolation,
) -> dict[str, int]:
    """Require one unique, valid level assignment for every candidate and no others."""
    expected_ids = {candidate.candidate_id for candidate in candidates}
    returned_ids = [assignment.candidate_id for assignment in assignments]
    if len(returned_ids) != len(set(returned_ids)):
        raise _correction_error(detected_violation, "LLM returned duplicate candidate IDs")
    if set(returned_ids) != expected_ids:
        raise _correction_error(
            detected_violation, "LLM did not assign every heading candidate exactly once"
        )
    if any(assignment.level not in range(1, 7) for assignment in assignments):
        raise _correction_error(detected_violation, "LLM returned an invalid heading level")
    return {
        assignment.candidate_id: assignment.level for assignment in assignments
    }


def _validate_final_heading_sequence(
    structure_elements: list[tuple[Dictionary, int, int | None]],
    candidates: list[_HeadingCandidate],
    assignments_by_id: dict[str, int],
    role_map: Dictionary | None,
    detected_violation: DetectedViolation,
) -> None:
    """Prevent the LLM assignment from adding heading-level skips."""
    candidate_by_index = {
        candidate.document_index: candidate for candidate in candidates
    }
    original_levels: list[int] = []
    final_levels: list[int] = []
    for document_index, (element, _, _) in enumerate(structure_elements):
        candidate = candidate_by_index.get(document_index)
        existing_level = _numbered_heading_level(
            resolve_role(element.get("/S"), role_map)
        )
        if existing_level is not None:
            original_levels.append(existing_level)
            final_levels.append(existing_level)
        elif candidate is not None:
            final_levels.append(assignments_by_id[candidate.candidate_id])

    if _heading_skip_count(final_levels) > _heading_skip_count(original_levels):
        raise _correction_error(
            detected_violation, "LLM assignment would add a heading-level skip"
        )


def _heading_skip_count(levels: list[int]) -> int:
    """Count descending outline jumps, including a first heading above /H1."""
    if not levels:
        return 0
    skips = 1 if levels[0] > 1 else 0
    return skips + sum(
        current > previous + 1
        for previous, current in zip(levels, levels[1:])
    )


def _numbered_heading_level(role: object) -> int | None:
    """Convert a standard /H1 through /H6 role into its numeric level."""
    if role not in _NUMBERED_HEADING_TAGS:
        return None
    return int(str(role)[2:])


def _correction_error(
    detected_violation: DetectedViolation,
    reason: str,
) -> CouldNotCorrectDetectedViolationException:
    """Create a correction exception containing the violation name and reason."""
    return CouldNotCorrectDetectedViolationException(
        f"{detected_violation.violation.name}: {reason}"
    )
