import importlib
import json
from unittest.mock import MagicMock, patch

import pikepdf
import pytest

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.LLM.image import Image
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle import (
    correct_figure_structure_alternate_description_missing,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    generate_resource_path,
    run_generic_corrector_test,
)


corrector_module = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax."
    "syntax_correctors_5_brian_karle.7_3_t01_figure_structure_alternate_description_missing"
)


def _detected_violation(figure: pikepdf.Object) -> DetectedViolation:
    """Create the violation object expected by the corrector."""
    return DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name="figure-structure-alternate-description-missing",
            description="",
            guidelines=[],
        ),
        affected_element=figure,
        supplementary_information=[],
    )


@pytest.fixture(autouse=True)
def an_ai_is_set_up(monkeypatch):
    """These tests simulate the AI's answers, so the corrector must believe an AI is set up."""
    import pdfaccessguru.LLM.fallback as fallback
    monkeypatch.setattr(fallback, "ai_available", lambda: True)


def _figure(pdf: pikepdf.Pdf) -> pikepdf.Dictionary:
    """Resolve the affected Figure without optional chained accesses."""
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    assert isinstance(structure_tree_root, pikepdf.Dictionary)
    root_children = structure_tree_root.get("/K")
    assert isinstance(root_children, pikepdf.Array)

    document = root_children[0]
    assert isinstance(document, pikepdf.Dictionary)
    document_children = document.get("/K")
    assert isinstance(document_children, pikepdf.Array)

    paragraph = document_children[1]
    assert isinstance(paragraph, pikepdf.Dictionary)
    paragraph_children = paragraph.get("/K")
    assert isinstance(paragraph_children, pikepdf.Array)

    figure = paragraph_children[0]
    assert isinstance(figure, pikepdf.Dictionary)
    return figure


@patch.object(corrector_module, "generate_figure_alt_text", return_value="Company logo")
def test_correct_figure_structure_alternate_description_missing(
    mock_generate_alt_text: MagicMock,
):
    """Correct the corpus violation and verify vision and structure context."""
    run_generic_corrector_test(
        rule_id="7.3-1",
        test_pdf_file="veraPDF_corpus/7.3-t01-fail-a.pdf",
        corrector=correct_figure_structure_alternate_description_missing,
        context=(
            "root/document[0]/StructTreeRoot[0](17 0 obj PDStructTreeRoot)"
            "/K[0](23 0 obj SEDocument Document)"
            "/K[1](21 0 obj SEP P)"
            "/K[0](20 0 obj SEFigure Figure)"
        ),
        affected_element_detector=_figure,
    )

    mock_generate_alt_text.assert_called_once()
    call_args = mock_generate_alt_text.call_args
    assert call_args is not None
    context_json, figure_image = call_args.args
    assert isinstance(context_json, str)
    assert isinstance(figure_image, Image)
    assert figure_image.image_data.startswith(b"\x89PNG\r\n\x1a\n")

    context = json.loads(context_json)
    assert context["figure"]["tag"] == "/Figure"
    assert context["figure"]["direct_mcids"] == [1]
    assert context["parent"]["tag"] == "/P"
    assert context["document_language"] == "en-US"
    assert "company" in context["page_text_context"]


@patch.object(corrector_module, "generate_figure_alt_text", return_value="Company logo")
def test_corrector_writes_generated_alt_text(_mock_generate_alt_text: MagicMock):
    pdf_path = generate_resource_path("veraPDF_corpus/7.3-t01-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        figure = _figure(pdf)

        correct_figure_structure_alternate_description_missing(
            _detected_violation(figure), pdf
        )

        assert str(figure.get("/Alt")) == "Company logo"
        assert figure.get("/ActualText") is None


@patch.object(corrector_module, "generate_figure_alt_text", return_value="Company logo")
def test_corrector_reuses_identical_alt_text_request(
    mock_generate_alt_text: MagicMock,
):
    pdf_path = generate_resource_path("veraPDF_corpus/7.3-t01-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        figure = _figure(pdf)

        correct_figure_structure_alternate_description_missing(
            _detected_violation(figure), pdf
        )
        del figure["/Alt"]
        correct_figure_structure_alternate_description_missing(
            _detected_violation(figure), pdf
        )

        assert str(figure.get("/Alt")) == "Company logo"
    mock_generate_alt_text.assert_called_once()


@patch.object(corrector_module.OpenRouterBaseProvider, "send_message_with_image")
def test_generate_figure_alt_text_uses_image_and_json_mode(
    mock_send_message: MagicMock,
):
    mock_send_message.return_value = '{"alt_text": "A blue company logo"}'
    image = Image(b"png-data")

    assert corrector_module.generate_figure_alt_text("{}", image) == (
        "A blue company logo"
    )
    assert mock_send_message.call_args.args[2] is image
    assert mock_send_message.call_args.kwargs == {"json_mode": True}


@patch.object(corrector_module.OpenRouterBaseProvider, "send_message_with_image")
def test_a_broken_ai_answer_falls_back_to_the_text_around_the_picture(
    mock_send_message: MagicMock,
):
    """Since Phase 4 an unusable AI answer does not leave the picture without a description."""
    mock_send_message.side_effect = KeyError("choices")
    pdf_path = generate_resource_path("veraPDF_corpus/7.3-t01-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        figure = _figure(pdf)
        correct_figure_structure_alternate_description_missing(_detected_violation(figure), pdf)
        assert str(figure.get("/Alt")).strip()
    mock_send_message.assert_called_once()


@patch.object(corrector_module, "generate_figure_alt_text", return_value="   ")
def test_an_empty_ai_answer_falls_back_to_the_text_around_the_picture(
    _mock_generate_alt_text: MagicMock,
):
    pdf_path = generate_resource_path("veraPDF_corpus/7.3-t01-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        figure = _figure(pdf)
        correct_figure_structure_alternate_description_missing(_detected_violation(figure), pdf)
        assert str(figure.get("/Alt")).strip()


@patch.object(corrector_module, "generate_figure_alt_text")
def test_corrector_preserves_existing_actual_text(mock_generate_alt_text: MagicMock):
    pdf_path = generate_resource_path("veraPDF_corpus/7.3-t01-pass-b.pdf")
    with pikepdf.open(pdf_path) as pdf:
        figure = _figure(pdf)
        existing_actual_text = str(figure.get("/ActualText"))

        correct_figure_structure_alternate_description_missing(
            _detected_violation(figure), pdf
        )

        assert str(figure.get("/ActualText")) == existing_actual_text
        assert figure.get("/Alt") is None
    mock_generate_alt_text.assert_not_called()


@patch.object(corrector_module, "generate_figure_alt_text", return_value="Company logo")
def test_corrector_supports_custom_figure_tag_via_role_map(
    _mock_generate_alt_text: MagicMock,
):
    pdf_path = generate_resource_path("veraPDF_corpus/7.3-t01-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        structure_tree_root = pdf.Root.get("/StructTreeRoot")
        assert isinstance(structure_tree_root, pikepdf.Dictionary)
        structure_tree_root["/RoleMap"] = pikepdf.Dictionary(
            {"/CustomFigure": pikepdf.Name("/Figure")}
        )
        figure = _figure(pdf)
        figure["/S"] = pikepdf.Name("/CustomFigure")

        correct_figure_structure_alternate_description_missing(
            _detected_violation(figure), pdf
        )

        assert str(figure.get("/Alt")) == "Company logo"


def test_render_figure_falls_back_to_mcid_bounds_without_bbox():
    """Figures without layout attributes can still be isolated through their MCID."""
    pdf_path = generate_resource_path("veraPDF_corpus/7.3-t01-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        figure = _figure(pdf)
        if "/A" in figure:
            del figure["/A"]

        rendered = corrector_module._render_figure(
            pdf, figure, _detected_violation(figure)
        )

        assert rendered.image.image_data.startswith(b"\x89PNG\r\n\x1a\n")
        assert rendered.crop_bbox != (0.0, 0.0, 612.0, 792.0)
