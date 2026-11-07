import importlib
import json
from typing import cast
from unittest.mock import patch

import pikepdf
import pytest

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle import (
    correct_table_columns_different_number_rows,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    generate_resource_path,
)


corrector_module = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax."
    "syntax_correctors_5_brian_karle.7_2_t41_table_columns_different_number_rows"
)


def _detected_violation(table: pikepdf.Object) -> DetectedViolation:
    return DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name="table-columns-different-number-rows",
            description="",
            guidelines=[],
        ),
        affected_element=table,
        supplementary_information=[],
    )


def _table(pdf: pikepdf.Pdf) -> pikepdf.Dictionary:
    table = pdf.Root["/StructTreeRoot"]["/K"][0]["/K"][1]
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
    return cast(pikepdf.Dictionary, table_attributes)


def _row_span(cell: pikepdf.Object) -> int:
    row_span = _table_attributes(cell).get("/RowSpan")
    assert row_span is not None
    return int(str(row_span))


@patch.object(corrector_module, "determine_correct_row_count", return_value=3)
def test_correct_table_columns_different_number_rows(mock_determine):
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t41-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        first_header = table["/K"][0]["/K"][0]

        assert _row_span(first_header) == 5
        correct_table_columns_different_number_rows(_detected_violation(table), pdf)
        assert _row_span(first_header) == 3

    sent_table = json.loads(mock_determine.call_args.args[0])
    assert sent_table["explicit_tr_count"] == 3
    assert sent_table["column_heights"] == [5, 3, 3, 3, 3]
    assert sent_table["candidate_row_counts"] == [3, 5]
    assert len(sent_table["cells"]) == 12


@patch.object(corrector_module, "determine_correct_row_count", return_value=5)
def test_corrector_can_extend_shorter_columns(_mock_determine):
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t41-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        last_row = table["/K"][2]

        correct_table_columns_different_number_rows(_detected_violation(table), pdf)

        for cell in last_row["/K"]:
            assert _row_span(cell) == 3


@patch.object(corrector_module, "determine_correct_row_count", return_value=2)
def test_corrector_supports_sections_colspans_and_revised_attributes(_mock_determine):
    """The correction must not depend on the structure of the corpus PDF."""
    pdf = pikepdf.Pdf.new()
    obsolete_table_attributes = pikepdf.Dictionary(
        {"/O": pikepdf.Name("/Table"), "/RowSpan": 9}
    )
    effective_table_attributes = pikepdf.Dictionary(
        {
            "/O": pikepdf.Name("/Table"),
            "/RowSpan": 4,
            "/ColSpan": 2,
        }
    )
    spanning_header = pikepdf.Dictionary(
        {
            "/S": pikepdf.Name("/TH"),
            "/A": pikepdf.Array(
                [obsolete_table_attributes, effective_table_attributes]
            ),
        }
    )
    first_row = pikepdf.Dictionary(
        {
            "/S": pikepdf.Name("/TR"),
            "/K": pikepdf.Array(
                [spanning_header, pikepdf.Dictionary({"/S": pikepdf.Name("/TH")})]
            ),
        }
    )
    second_row = pikepdf.Dictionary(
        {
            "/S": pikepdf.Name("/TR"),
            "/K": pikepdf.Dictionary({"/S": pikepdf.Name("/TD")}),
        }
    )
    table = pikepdf.Dictionary(
        {
            "/S": pikepdf.Name("/Table"),
            "/K": pikepdf.Dictionary(
                {
                    "/S": pikepdf.Name("/TBody"),
                    "/K": pikepdf.Array([first_row, second_row]),
                }
            ),
        }
    )

    correct_table_columns_different_number_rows(_detected_violation(table), pdf)

    assert int(str(obsolete_table_attributes["/RowSpan"])) == 9
    assert int(str(effective_table_attributes["/RowSpan"])) == 2
    assert int(str(effective_table_attributes["/ColSpan"])) == 2


@patch.object(corrector_module, "determine_correct_row_count", return_value=2)
def test_corrector_resolves_custom_tags_from_role_map(_mock_determine):
    pdf = pikepdf.Pdf.new()
    pdf.Root["/StructTreeRoot"] = pikepdf.Dictionary(
        {
            "/RoleMap": pikepdf.Dictionary(
                {
                    "/CustomTable": pikepdf.Name("/Table"),
                    "/CustomRow": pikepdf.Name("/TR"),
                    "/CustomHeader": pikepdf.Name("/TH"),
                    "/CustomCell": pikepdf.Name("/TD"),
                }
            )
        }
    )
    spanning_header = pikepdf.Dictionary(
        {
            "/S": pikepdf.Name("/CustomHeader"),
            "/A": pikepdf.Dictionary(
                {"/O": pikepdf.Name("/Table"), "/RowSpan": 3}
            ),
        }
    )
    table = pikepdf.Dictionary(
        {
            "/S": pikepdf.Name("/CustomTable"),
            "/K": pikepdf.Array(
                [
                    pikepdf.Dictionary(
                        {
                            "/S": pikepdf.Name("/CustomRow"),
                            "/K": pikepdf.Array(
                                [
                                    spanning_header,
                                    pikepdf.Dictionary(
                                        {"/S": pikepdf.Name("/CustomHeader")}
                                    ),
                                ]
                            ),
                        }
                    ),
                    pikepdf.Dictionary(
                        {
                            "/S": pikepdf.Name("/CustomRow"),
                            "/K": pikepdf.Dictionary(
                                {"/S": pikepdf.Name("/CustomCell")}
                            ),
                        }
                    ),
                ]
            ),
        }
    )

    correct_table_columns_different_number_rows(_detected_violation(table), pdf)

    assert _row_span(spanning_header) == 2


@patch.object(corrector_module.OpenRouterBaseProvider, "send_message")
def test_determine_correct_row_count_uses_json_mode(mock_send_message):
    mock_send_message.return_value = '{"correct_row_count": 3}'

    assert corrector_module.determine_correct_row_count("{}") == 3
    assert mock_send_message.call_args.kwargs == {"json_mode": True}


@patch.object(corrector_module.OpenRouterBaseProvider, "send_message", return_value="not json")
def test_determine_correct_row_count_rejects_invalid_response(_mock_send_message):
    with pytest.raises(CouldNotCorrectDetectedViolationException):
        corrector_module.determine_correct_row_count("{}")


@patch.object(corrector_module, "determine_correct_row_count", return_value=4)
def test_corrector_rejects_hallucinated_row_count(_mock_determine):
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t41-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        first_header = table["/K"][0]["/K"][0]

        with pytest.raises(CouldNotCorrectDetectedViolationException):
            correct_table_columns_different_number_rows(_detected_violation(table), pdf)
        assert _row_span(first_header) == 5
