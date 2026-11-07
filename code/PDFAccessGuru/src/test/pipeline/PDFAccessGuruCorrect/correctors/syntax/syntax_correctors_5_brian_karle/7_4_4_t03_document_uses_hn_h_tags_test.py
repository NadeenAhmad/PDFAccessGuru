import pytest
import importlib
import json
from unittest.mock import MagicMock, patch

import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle import (
    correct_document_uses_hn_h_tags,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    generate_resource_path,
    generate_test_result_path,
    run_generic_corrector_test,
)


corrector_module = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax."
    "syntax_correctors_5_brian_karle.7_4_4_t03_document_uses_hn_h_tags"
)
numbered_heading_module = corrector_module._NUMBERED_HEADING_CORRECTOR_MODULE
HeadingAssignment = numbered_heading_module._HeadingAssignment


def _detected_violation(element: pikepdf.Object) -> DetectedViolation:
    """Create the violation object expected by the corrector."""
    return DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name="document-uses-hn-h-tags",
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


def _sections(pdf: pikepdf.Pdf) -> pikepdf.Array:
    """Return both top-level sections from the corpus document."""
    sections = _document(pdf).get("/K")
    assert isinstance(sections, pikepdf.Array)
    return sections


def _heading(section: pikepdf.Object) -> pikepdf.Dictionary:
    """Return the first heading child of a section."""
    assert isinstance(section, pikepdf.Dictionary)
    children = section.get("/K")
    assert isinstance(children, pikepdf.Array)
    heading = children[0]
    assert isinstance(heading, pikepdf.Dictionary)
    return heading


def _reported_numbered_heading(pdf: pikepdf.Pdf) -> pikepdf.Dictionary:
    """Resolve the numbered heading on which veraPDF reports T03."""
    return _heading(_sections(pdf)[1])


@patch.object(
    numbered_heading_module,
    "determine_numbered_heading_tags",
    return_value=[HeadingAssignment("candidate-h-1", 1)],
)
def test_correct_document_uses_hn_h_tags(mock_determine: MagicMock):
    """Correct T03 and verify that both mixed-heading reports disappear."""
    run_generic_corrector_test(
        rule_id="7.4.4-3",
        test_pdf_file="veraPDF_corpus/7.4.4-t03-fail-a.pdf",
        corrector=correct_document_uses_hn_h_tags,
        context=(
            "root/document[0]/StructTreeRoot[0](18 0 obj PDStructTreeRoot)"
            "/K[0](19 0 obj SEDocument Document)"
            "/K[1](26 0 obj SESect Sect)"
            "/K[0](23 0 obj SEHn H1)"
        ),
        affected_element_detector=_reported_numbered_heading,
    )

    mock_determine.assert_called_once()
    call_args = mock_determine.call_args
    assert call_args is not None
    context_json = call_args.args[0]
    assert isinstance(context_json, str)
    context = json.loads(context_json)
    assert context["candidate_ids"] == ["candidate-h-1"]
    candidate = next(
        node
        for node in context["structure_nodes_in_document_order"]
        if node["is_candidate"]
    )
    assert candidate["text"] == "Heading"

    corrected_path = generate_test_result_path(
        "veraPDF_corpus/7.4.4-t03-fail-a_corrected.pdf"
    )
    remaining_rule_ids = {
        violation.rule_id for violation in run_verapdf(corrected_path)
    }
    assert "7.4.4-2" not in remaining_rule_ids
    assert "7.4.4-3" not in remaining_rule_ids


@patch.object(
    numbered_heading_module,
    "determine_numbered_heading_tags",
    return_value=[HeadingAssignment("candidate-h-1", 1)],
)
def test_corrector_numbers_only_the_unnumbered_heading(
    _mock_determine: MagicMock,
):
    pdf_path = generate_resource_path("veraPDF_corpus/7.4.4-t03-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        sections = _sections(pdf)
        unnumbered_heading = _heading(sections[0])
        existing_numbered_heading = _heading(sections[1])

        correct_document_uses_hn_h_tags(
            _detected_violation(existing_numbered_heading), pdf
        )

        assert str(unnumbered_heading.get("/S")) == "/H1"
        assert str(existing_numbered_heading.get("/S")) == "/H1"


@patch.object(corrector_module, "_correct_mixed_heading_tags")
def test_corrector_delegates_to_shared_general_engine(
    mock_shared_corrector: MagicMock,
):
    """T03 uses the same context and validation engine as T02."""
    pdf = pikepdf.Pdf.new()
    element = pikepdf.Dictionary({"/S": pikepdf.Name("/H1")})
    violation = _detected_violation(element)

    correct_document_uses_hn_h_tags(violation, pdf)

    mock_shared_corrector.assert_called_once_with(violation, pdf)


@pytest.fixture(autouse=True)
def an_ai_is_set_up(monkeypatch):
    """These tests simulate the AI's answers, so the corrector must believe an AI is set up
    (since Phase 5 it checks that before reading the whole document)."""
    import pdfaccessguru.LLM.fallback as fallback
    monkeypatch.setattr(fallback, "ai_available", lambda: True)
