import importlib
import io
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
    correct_table_several_captions,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    generate_resource_path,
    run_generic_corrector_test,
)


corrector_module = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax."
    "syntax_correctors_5_brian_karle.7_2_t39_table_several_captions"
)


def _table(pdf: pikepdf.Pdf) -> pikepdf.Dictionary:
    """Resolve the affected Table without optional chained accesses."""
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    assert isinstance(structure_tree_root, pikepdf.Dictionary)
    root_children = structure_tree_root.get("/K")
    assert isinstance(root_children, pikepdf.Array)
    document = root_children[0]
    assert isinstance(document, pikepdf.Dictionary)
    table = document.get("/K")
    assert isinstance(table, pikepdf.Dictionary)
    return table


def _captions(table: pikepdf.Dictionary) -> list[pikepdf.Dictionary]:
    """Return the direct Caption children of a test Table."""
    children = table.get("/K")
    assert isinstance(children, pikepdf.Array)
    return [
        child
        for child in children
        if isinstance(child, pikepdf.Dictionary) and str(child.get("/S")) == "/Caption"
    ]


def _detected_violation(table: pikepdf.Object) -> DetectedViolation:
    """Create the violation object expected by the corrector."""
    return DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name="table-several-captions",
            description="",
            guidelines=[],
        ),
        affected_element=table,
        supplementary_information=[],
    )


def _parent_tree_array(pdf: pikepdf.Pdf, key: int = 0) -> pikepdf.Array:
    """Resolve one page-parent array through the complete ParentTree number tree."""
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    assert isinstance(structure_tree_root, pikepdf.Dictionary)
    parent_tree_object = structure_tree_root.get("/ParentTree")
    assert isinstance(parent_tree_object, pikepdf.Dictionary)
    parent_value = pikepdf.NumberTree(parent_tree_object).get(key)
    assert isinstance(parent_value, pikepdf.Array)
    return parent_value


def _parent_tree_objgens(pdf: pikepdf.Pdf) -> set[tuple[int, int]]:
    """Collect every indirect structure element referenced by the ParentTree."""
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    assert isinstance(structure_tree_root, pikepdf.Dictionary)
    parent_tree_object = structure_tree_root.get("/ParentTree")
    assert isinstance(parent_tree_object, pikepdf.Dictionary)
    result: set[tuple[int, int]] = set()
    for value in pikepdf.NumberTree(parent_tree_object).values():
        targets = list(value) if isinstance(value, pikepdf.Array) else [value]
        for target in targets:
            if isinstance(target, pikepdf.Dictionary):
                result.add(target.objgen)
    return result


def _append_caption_marked_content(pdf: pikepdf.Pdf) -> None:
    """Add real MCID operators so the ParentTree test is not structure-only."""
    page_object = pdf.pages[0].obj
    assert isinstance(page_object, pikepdf.Dictionary)
    stream = pdf.make_stream(
        b"/Span <</MCID 0>> BDC EMC\n/Span <</MCID 1>> BDC EMC\n"
    )
    contents = page_object.get("/Contents")
    if isinstance(contents, pikepdf.Array):
        contents.append(stream)
    elif contents is None:
        page_object["/Contents"] = stream
    else:
        page_object["/Contents"] = pikepdf.Array([contents, stream])


@patch.object(
    corrector_module,
    "determine_correct_caption",
    return_value=corrector_module._CaptionDecision("caption-1", None),
)
def test_correct_table_several_captions(mock_determine_caption: MagicMock):
    """Correct the corpus violation and pass image plus bounded context to the LLM."""
    run_generic_corrector_test(
        rule_id="7.2-39",
        test_pdf_file="PDFAccessGuru_corpus/7.2-t39-fail-a.pdf",
        corrector=correct_table_several_captions,
        context=(
            "root/document[0]/StructTreeRoot[0](7 0 obj PDStructTreeRoot)"
            "/K[0](14 0 obj SEDocument Document)"
            "/K[0](24 0 obj SETable Table)"
        ),
        affected_element_detector=_table,
    )

    mock_determine_caption.assert_called_once()
    call_args = mock_determine_caption.call_args
    assert call_args is not None
    context_json, table_image = call_args.args
    assert isinstance(table_image, Image)
    assert table_image.image_data.startswith(b"\x89PNG\r\n\x1a\n")
    context = json.loads(context_json)
    assert context["table"]["tag"] == "/Table"
    assert "TH1" in context["table"]["extracted_text"]
    assert [caption["caption_id"] for caption in context["captions"]] == [
        "caption-1",
        "caption-2",
    ]


@patch.object(
    corrector_module,
    "determine_correct_caption",
    return_value=corrector_module._CaptionDecision("caption-2", None),
)
def test_corrector_keeps_selected_caption_and_all_non_caption_children(
    _mock_determine_caption: MagicMock,
):
    """Selecting a candidate removes only the other Caption elements."""
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t39-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        original_captions = _captions(table)
        children = table.get("/K")
        assert isinstance(children, pikepdf.Array)
        non_caption_count = len(children) - len(original_captions)
        selected_objgen = original_captions[1].objgen

        correct_table_several_captions(_detected_violation(table), pdf)

        remaining_captions = _captions(table)
        corrected_children = table.get("/K")
        assert isinstance(corrected_children, pikepdf.Array)
        assert len(remaining_captions) == 1
        assert remaining_captions[0].objgen == selected_objgen
        assert len(corrected_children) == non_caption_count + 1


@patch.object(
    corrector_module,
    "determine_correct_caption",
    return_value=corrector_module._CaptionDecision(
        None, "Quarterly revenue by region"
    ),
)
def test_corrector_replaces_wrong_captions_with_generated_accessible_text(
    _mock_determine_caption: MagicMock,
):
    """A generated caption replaces all candidates through one /ActualText value."""
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t39-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)

        correct_table_several_captions(_detected_violation(table), pdf)

        remaining_captions = _captions(table)
        assert len(remaining_captions) == 1
        assert str(remaining_captions[0].get("/ActualText")) == (
            "Quarterly revenue by region"
        )


@patch.object(corrector_module.OpenRouterBaseProvider, "send_message_with_image")
def test_determine_correct_caption_uses_vision_and_json_mode(
    mock_send_message: MagicMock,
):
    """The semantic decision is delegated to the vision-capable provider."""
    mock_send_message.return_value = (
        '{"selected_caption_id":"caption-2","generated_caption":null}'
    )
    image = Image(b"png-data")

    decision = corrector_module.determine_correct_caption("{}", image)

    assert decision == corrector_module._CaptionDecision("caption-2", None)
    assert mock_send_message.call_args.args[2] is image
    assert mock_send_message.call_args.kwargs == {"json_mode": True}


@patch.object(
    corrector_module,
    "determine_correct_caption",
    return_value=corrector_module._CaptionDecision("caption-99", None),
)
def test_corrector_rejects_unknown_caption_without_modifying_table(
    _mock_determine_caption: MagicMock,
):
    """An invented candidate ID cannot trigger a partial structure mutation."""
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t39-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)

        with pytest.raises(CouldNotCorrectDetectedViolationException):
            correct_table_several_captions(_detected_violation(table), pdf)

        assert len(_captions(table)) == 2


def test_corrector_rejects_more_than_ten_captions_before_calling_llm():
    """The correction strategy's ten-Caption input limit is enforced."""
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t39-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        children = table.get("/K")
        assert isinstance(children, pikepdf.Array)
        for _ in range(9):
            children.append(pikepdf.Dictionary({"/S": pikepdf.Name("/Caption")}))

        with patch.object(corrector_module, "determine_correct_caption") as determine:
            with pytest.raises(CouldNotCorrectDetectedViolationException):
                correct_table_several_captions(_detected_violation(table), pdf)
            determine.assert_not_called()


def test_corrector_does_nothing_when_only_one_caption_remains():
    """An already compliant Table does not require rendering or an LLM call."""
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t39-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        children = table.get("/K")
        assert isinstance(children, pikepdf.Array)
        del children[-1]

        with patch.object(corrector_module, "determine_correct_caption") as determine:
            correct_table_several_captions(_detected_violation(table), pdf)
            determine.assert_not_called()
        assert len(_captions(table)) == 1


@patch.object(
    corrector_module,
    "determine_correct_caption",
    return_value=corrector_module._CaptionDecision("caption-2", None),
)
def test_corrector_transfers_marked_content_and_removes_stale_parent_tree_links(
    _mock_determine_caption: MagicMock,
):
    """Removed Caption MCIDs remain reachable without stale ParentTree targets."""
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t39-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        captions = _captions(table)
        removed_objgen = captions[0].objgen
        selected_objgen = captions[1].objgen

        # The corpus Captions are empty, so add non-vacuous marked-content mappings.
        captions[0]["/K"] = pikepdf.Array([0])
        captions[1]["/K"] = pikepdf.Array([1])
        _append_caption_marked_content(pdf)
        parent_array = _parent_tree_array(pdf)
        parent_array[0] = captions[0]
        parent_array[1] = captions[1]

        correct_table_several_captions(_detected_violation(table), pdf)

        remaining = _captions(table)
        assert len(remaining) == 1
        assert remaining[0].objgen == selected_objgen
        remaining_kids = remaining[0].get("/K")
        assert isinstance(remaining_kids, pikepdf.Array)
        assert [int(kid) for kid in remaining_kids] == [0, 1]
        assert parent_array[0].objgen == selected_objgen
        assert parent_array[1].objgen == selected_objgen
        assert removed_objgen not in _parent_tree_objgens(pdf)
        assert captions[0].get("/K") is None
        assert captions[0].get("/P") is None

        # Reopen the serialized PDF to verify persisted references, not wrappers only.
        output = io.BytesIO()
        pdf.save(output)
        output.seek(0)
        with pikepdf.open(output) as reopened_pdf:
            reopened_table = _table(reopened_pdf)
            reopened_caption = _captions(reopened_table)[0]
            reopened_parent_array = _parent_tree_array(reopened_pdf)
            assert reopened_parent_array[0].objgen == reopened_caption.objgen
            assert reopened_parent_array[1].objgen == reopened_caption.objgen
            assert removed_objgen not in _parent_tree_objgens(reopened_pdf)


@patch.object(
    corrector_module,
    "determine_correct_caption",
    return_value=corrector_module._CaptionDecision("caption-2", None),
)
def test_corrector_rejects_owned_mcid_without_parent_tree_before_modification(
    _mock_determine_caption: MagicMock,
):
    """Missing mandatory mapping data cannot cause a partial structure edit."""
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t39-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        captions = _captions(table)
        captions[0]["/K"] = pikepdf.Array([0])
        structure_tree_root = pdf.Root.get("/StructTreeRoot")
        assert isinstance(structure_tree_root, pikepdf.Dictionary)
        del structure_tree_root["/ParentTree"]

        with pytest.raises(CouldNotCorrectDetectedViolationException):
            correct_table_several_captions(_detected_violation(table), pdf)

        assert len(_captions(table)) == 2
        assert [int(kid) for kid in captions[0]["/K"]] == [0]
        assert len(captions[1]["/K"]) == 0


@patch.object(
    corrector_module,
    "determine_correct_caption",
    return_value=corrector_module._CaptionDecision("caption-2", None),
)
def test_corrector_allows_empty_caption_removal_without_parent_tree(
    _mock_determine_caption: MagicMock,
):
    """A ParentTree is optional when removed Captions own no marked content."""
    pdf_path = generate_resource_path("PDFAccessGuru_corpus/7.2-t39-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        structure_tree_root = pdf.Root.get("/StructTreeRoot")
        assert isinstance(structure_tree_root, pikepdf.Dictionary)
        del structure_tree_root["/ParentTree"]

        correct_table_several_captions(_detected_violation(table), pdf)

        assert len(_captions(table)) == 1
