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
    correct_table_rows_span_different_number_columns,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    generate_resource_path,
    run_generic_corrector_test,
)


corrector_module = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax."
    "syntax_correctors_5_brian_karle.7_2_t42_table_rows_span_different_number_columns"
)


def _detected_violation(table: pikepdf.Object) -> DetectedViolation:
    return DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name="table-rows-span-different-number-columns",
            description="",
            guidelines=[],
        ),
        affected_element=table,
        supplementary_information=[],
    )


def _table(pdf: pikepdf.Pdf) -> pikepdf.Dictionary:
    table = pdf.Root["/StructTreeRoot"]["/K"][0]["/K"]
    assert isinstance(table, pikepdf.Dictionary)
    return table


def _table_attributes(cell: pikepdf.Object) -> pikepdf.Dictionary:
    assert isinstance(cell, pikepdf.Dictionary)
    attributes = cell.get("/A")
    attributes = (
        list(attributes) if isinstance(attributes, pikepdf.Array) else [attributes]
    )
    table_attributes = next(
        item
        for item in reversed(attributes)
        if isinstance(item, pikepdf.Dictionary)
        and item.get("/O") == pikepdf.Name("/Table")
    )
    assert isinstance(table_attributes, pikepdf.Dictionary)
    return table_attributes


def _column_span(cell: pikepdf.Object) -> int:
    column_span = _table_attributes(cell).get("/ColSpan")
    assert column_span is not None
    return int(str(column_span))


@patch.object(corrector_module, "determine_correct_column_count", return_value=4)
def test_correct_table_rows_span_different_number_columns(mock_determine):
    """The corpus violation is removed and the complete table is sent to the LLM."""
    run_generic_corrector_test(
        rule_id="7.2-42",
        test_pdf_file="veraPDF_corpus/7.2-t42-fail-a.pdf",
        corrector=correct_table_rows_span_different_number_columns,
        context=(
            "root/document[0]/StructTreeRoot[0](6 0 obj PDStructTreeRoot)"
            "/K[0](14 0 obj SEDocument Document)"
            "/K[0](24 0 obj SETable Table)"
        ),
        affected_element_detector=_table,
    )

    mock_determine.assert_called_once()
    call_args = mock_determine.call_args
    assert call_args is not None
    table_json = call_args.args[0]
    assert isinstance(table_json, str)
    sent_table = json.loads(mock_determine.call_args.args[0])
    assert sent_table["explicit_tr_count"] == 5
    assert sent_table["row_widths"] == [3, 4, 4, 4, 4]
    assert sent_table["candidate_column_counts"] == [3, 4]
    assert len(sent_table["cells"]) == 16


@patch.object(corrector_module, "determine_correct_column_count", return_value=4)
def test_corrector_changes_only_the_required_colspan(_mock_determine):
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t42-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        first_row_last_header = table["/K"][0]["/K"][1]

        assert _column_span(first_row_last_header) == 2
        correct_table_rows_span_different_number_columns(
            _detected_violation(table), pdf
        )
        assert _column_span(first_row_last_header) == 3


@patch.object(corrector_module, "determine_correct_column_count", return_value=4)
def test_corrector_supports_sections_role_maps_and_revised_attributes(_mock_determine):
    """The algorithm must not depend on the layout of the corpus PDF."""
    pdf = pikepdf.Pdf.new()
    pdf.Root["/StructTreeRoot"] = pikepdf.Dictionary(
        {
            "/RoleMap": pikepdf.Dictionary(
                {
                    "/CustomTable": pikepdf.Name("/Table"),
                    "/CustomBody": pikepdf.Name("/TBody"),
                    "/CustomRow": pikepdf.Name("/TR"),
                    "/CustomCell": pikepdf.Name("/TD"),
                }
            )
        }
    )
    obsolete_attributes = pikepdf.Dictionary(
        {"/O": pikepdf.Name("/Table"), "/ColSpan": 7}
    )
    effective_attributes = pikepdf.Dictionary(
        {"/O": pikepdf.Name("/Table"), "/ColSpan": 5}
    )
    wide_cell = pikepdf.Dictionary(
        {
            "/S": pikepdf.Name("/CustomCell"),
            "/A": pikepdf.Array([obsolete_attributes, effective_attributes]),
        }
    )
    first_row = pikepdf.Dictionary(
        {"/S": pikepdf.Name("/CustomRow"), "/K": wide_cell}
    )
    second_row = pikepdf.Dictionary(
        {
            "/S": pikepdf.Name("/CustomRow"),
            "/K": pikepdf.Array(
                [
                    pikepdf.Dictionary({"/S": pikepdf.Name("/CustomCell")})
                    for _ in range(4)
                ]
            ),
        }
    )
    table = pikepdf.Dictionary(
        {
            "/S": pikepdf.Name("/CustomTable"),
            "/K": pikepdf.Dictionary(
                {
                    "/S": pikepdf.Name("/CustomBody"),
                    "/K": pikepdf.Array([first_row, second_row]),
                }
            ),
        }
    )

    correct_table_rows_span_different_number_columns(
        _detected_violation(table), pdf
    )

    assert int(str(obsolete_attributes["/ColSpan"])) == 7
    assert int(str(effective_attributes["/ColSpan"])) == 4


@patch.object(corrector_module.OpenRouterBaseProvider, "send_message")
def test_determine_correct_column_count_uses_json_mode(mock_send_message):
    mock_send_message.return_value = '{"correct_column_count": 4}'

    assert corrector_module.determine_correct_column_count("{}") == 4
    assert mock_send_message.call_args.kwargs == {"json_mode": True}


@patch.object(
    corrector_module.OpenRouterBaseProvider,
    "send_message",
    return_value="not json",
)
def test_determine_correct_column_count_rejects_invalid_response(_mock_send_message):
    with pytest.raises(CouldNotCorrectDetectedViolationException):
        corrector_module.determine_correct_column_count("{}")


@patch.object(corrector_module, "determine_correct_column_count", return_value=5)
def test_corrector_rejects_hallucinated_column_count(_mock_determine):
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t42-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        with pytest.raises(CouldNotCorrectDetectedViolationException):
            correct_table_rows_span_different_number_columns(
                _detected_violation(table), pdf
            )


@patch.object(corrector_module, "determine_correct_column_count", return_value=3)
def test_corrector_does_not_remove_complete_cells(_mock_determine):
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t42-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        first_row_last_header = table["/K"][0]["/K"][1]

        with pytest.raises(CouldNotCorrectDetectedViolationException):
            correct_table_rows_span_different_number_columns(
                _detected_violation(table), pdf
            )
        assert _column_span(first_row_last_header) == 2


@patch.object(corrector_module, "determine_correct_column_count", return_value=3)
def test_corrector_rejects_rowspan_collision_without_modifying_pdf(_mock_determine):
    pdf = pikepdf.Pdf.new()
    spanning_cell = pikepdf.Dictionary(
        {
            "/S": pikepdf.Name("/TD"),
            "/A": pikepdf.Dictionary(
                {
                    "/O": pikepdf.Name("/Table"),
                    "/RowSpan": 2,
                    "/ColSpan": 2,
                }
            ),
        }
    )
    table = pikepdf.Dictionary(
        {
            "/S": pikepdf.Name("/Table"),
            "/K": pikepdf.Array(
                [
                    pikepdf.Dictionary(
                        {"/S": pikepdf.Name("/TR"), "/K": spanning_cell}
                    ),
                    pikepdf.Dictionary(
                        {
                            "/S": pikepdf.Name("/TR"),
                            "/K": pikepdf.Dictionary({"/S": pikepdf.Name("/TD")}),
                        }
                    ),
                ]
            ),
        }
    )

    with pytest.raises(CouldNotCorrectDetectedViolationException):
        correct_table_rows_span_different_number_columns(
            _detected_violation(table), pdf
        )

    assert _column_span(spanning_cell) == 2
