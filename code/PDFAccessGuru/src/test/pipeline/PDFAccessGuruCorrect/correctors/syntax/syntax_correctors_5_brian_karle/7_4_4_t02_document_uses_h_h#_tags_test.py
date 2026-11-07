import importlib
import json
from unittest.mock import MagicMock, patch

import pikepdf
import pytest

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle import (
    correct_document_uses_h_h_sharp_tags,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    generate_resource_path,
    run_generic_corrector_test,
)


corrector_module = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax."
    "syntax_correctors_5_brian_karle.7_4_4_t02_document_uses_h_h_sharp_tags"
)
HeadingAssignment = corrector_module._HeadingAssignment


def _detected_violation(element: pikepdf.Object) -> DetectedViolation:
    """Create the violation object expected by the corrector."""
    return DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name="document-uses-h-h#-tags",
            description="",
            guidelines=[],
        ),
        affected_element=element,
        supplementary_information=[],
    )


def _document(pdf: pikepdf.Pdf) -> pikepdf.Dictionary:
    """Resolve the document structure element without optional chained accesses."""
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    assert isinstance(structure_tree_root, pikepdf.Dictionary)
    document = structure_tree_root.get("/K")
    assert isinstance(document, pikepdf.Dictionary)
    return document


def _unnumbered_heading(pdf: pikepdf.Pdf) -> pikepdf.Dictionary:
    """Resolve the unnumbered heading reported by veraPDF."""
    document = _document(pdf)
    sections = document.get("/K")
    assert isinstance(sections, pikepdf.Array)
    second_section = sections[1]
    assert isinstance(second_section, pikepdf.Dictionary)
    children = second_section.get("/K")
    assert isinstance(children, pikepdf.Array)
    heading = children[0]
    assert isinstance(heading, pikepdf.Dictionary)
    return heading


@patch.object(
    corrector_module,
    "determine_numbered_heading_tags",
    return_value=[HeadingAssignment("candidate-h-1", 1)],
)
def test_correct_document_uses_h_h_tags(mock_determine: MagicMock):
    """Correct the corpus violation and inspect the semantic LLM context."""
    run_generic_corrector_test(
        rule_id="7.4.4-2",
        test_pdf_file="veraPDF_corpus/7.4.4-t02-fail-a.pdf",
        corrector=correct_document_uses_h_h_sharp_tags,
        context=(
            "root/document[0]/StructTreeRoot[0](20 0 obj PDStructTreeRoot)"
            "/K[0](21 0 obj SEDocument Document)"
            "/K[1](28 0 obj SESect Sect)"
            "/K[0](25 0 obj SEH H)"
        ),
        affected_element_detector=_unnumbered_heading,
    )

    mock_determine.assert_called_once()
    call_args = mock_determine.call_args
    assert call_args is not None
    context_json = call_args.args[0]
    assert isinstance(context_json, str)
    context = json.loads(context_json)

    assert context["candidate_ids"] == ["candidate-h-1"]
    nodes = context["structure_nodes_in_document_order"]
    assert any(node["existing_heading_level"] == 1 for node in nodes)
    candidate = next(node for node in nodes if node["is_candidate"])
    assert candidate["text"] == "Heading"


@patch.object(
    corrector_module,
    "determine_numbered_heading_tags",
    return_value=[HeadingAssignment("candidate-h-1", 1)],
)
def test_corrector_replaces_unnumbered_heading_with_selected_level(
    _mock_determine: MagicMock,
):
    pdf_path = generate_resource_path("veraPDF_corpus/7.4.4-t02-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        heading = _unnumbered_heading(pdf)
        assert str(heading.get("/S")) == "/H"

        correct_document_uses_h_h_sharp_tags(
            _detected_violation(heading), pdf
        )

        assert str(heading.get("/S")) == "/H1"


@patch.object(corrector_module.OpenRouterBaseProvider, "send_message")
def test_determine_numbered_heading_tags_uses_json_mode(
    mock_send_message: MagicMock,
):
    mock_send_message.return_value = (
        '{"heading_assignments": [{"id": "candidate-h-1", "level": 2}]}'
    )

    assert corrector_module.determine_numbered_heading_tags("{}") == [
        HeadingAssignment("candidate-h-1", 2)
    ]
    assert mock_send_message.call_args.kwargs == {"json_mode": True}


@patch.object(
    corrector_module,
    "determine_numbered_heading_tags",
    return_value=[],
)
def test_corrector_rejects_missing_assignment_without_modifying_pdf(
    _mock_determine: MagicMock,
):
    pdf_path = generate_resource_path("veraPDF_corpus/7.4.4-t02-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        heading = _unnumbered_heading(pdf)

        with pytest.raises(CouldNotCorrectDetectedViolationException):
            correct_document_uses_h_h_sharp_tags(
                _detected_violation(heading), pdf
            )

        assert str(heading.get("/S")) == "/H"


@patch.object(
    corrector_module,
    "determine_numbered_heading_tags",
    return_value=[HeadingAssignment("candidate-h-1", 3)],
)
def test_corrector_rejects_heading_level_skip(_mock_determine: MagicMock):
    pdf_path = generate_resource_path("veraPDF_corpus/7.4.4-t02-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        heading = _unnumbered_heading(pdf)

        with pytest.raises(CouldNotCorrectDetectedViolationException):
            correct_document_uses_h_h_sharp_tags(
                _detected_violation(heading), pdf
            )

        assert str(heading.get("/S")) == "/H"


@patch.object(corrector_module, "determine_numbered_heading_tags")
def test_corrector_does_not_call_llm_when_document_has_only_numbered_headings(
    mock_determine: MagicMock,
):
    pdf_path = generate_resource_path("veraPDF_corpus/7.4.4-t02-pass-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        document = _document(pdf)

        correct_document_uses_h_h_sharp_tags(
            _detected_violation(document), pdf
        )

    mock_determine.assert_not_called()


@patch.object(
    corrector_module,
    "determine_numbered_heading_tags",
    return_value=[HeadingAssignment("candidate-h-1", 1)],
)
def test_corrector_supports_custom_h_tag_via_role_map(
    _mock_determine: MagicMock,
):
    pdf_path = generate_resource_path("veraPDF_corpus/7.4.4-t02-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        structure_tree_root = pdf.Root.get("/StructTreeRoot")
        assert isinstance(structure_tree_root, pikepdf.Dictionary)
        structure_tree_root["/RoleMap"] = pikepdf.Dictionary(
            {"/CustomHeading": pikepdf.Name("/H")}
        )
        heading = _unnumbered_heading(pdf)
        heading["/S"] = pikepdf.Name("/CustomHeading")

        correct_document_uses_h_h_sharp_tags(
            _detected_violation(heading), pdf
        )

        assert str(heading.get("/S")) == "/H1"


@pytest.fixture(autouse=True)
def an_ai_is_set_up(monkeypatch):
    """These tests simulate the AI's answers, so the corrector must believe an AI is set up
    (since Phase 5 it checks that before reading the whole document)."""
    import pdfaccessguru.LLM.fallback as fallback
    monkeypatch.setattr(fallback, "ai_available", lambda: True)
