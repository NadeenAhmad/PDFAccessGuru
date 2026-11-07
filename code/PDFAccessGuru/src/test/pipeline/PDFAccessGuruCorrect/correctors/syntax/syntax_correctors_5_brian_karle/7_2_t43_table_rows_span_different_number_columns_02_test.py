import importlib
import json
from unittest.mock import MagicMock, patch

import pikepdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle import (
    correct_table_rows_span_different_number_columns_02,
)
from test.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_corrector_test_utils import (
    generate_resource_path,
    run_generic_corrector_test,
)


corrector_module = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax."
    "syntax_correctors_5_brian_karle.7_2_t43_table_rows_span_different_number_columns_02"
)
column_count_module = corrector_module._COLUMN_COUNT_CORRECTOR_MODULE


def _detected_violation(table: pikepdf.Object) -> DetectedViolation:
    """Create the violation object expected by the corrector."""
    return DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name="table-rows-span-different-number-columns_02",
            description="",
            guidelines=[],
        ),
        affected_element=table,
        supplementary_information=[],
    )


def _table(pdf: pikepdf.Pdf) -> pikepdf.Dictionary:
    """Resolve the affected table without optional chained accesses."""
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    assert isinstance(structure_tree_root, pikepdf.Dictionary)

    structure_children = structure_tree_root.get("/K")
    assert isinstance(structure_children, pikepdf.Array)
    assert len(structure_children) > 0

    document = structure_children[0]
    assert isinstance(document, pikepdf.Dictionary)

    table = document.get("/K")
    assert isinstance(table, pikepdf.Dictionary)
    return table


def _table_attributes(cell: pikepdf.Object) -> pikepdf.Dictionary:
    """Return the effective table-owner attributes of a cell."""
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
    """Read a cell's explicit ColSpan, using one as the PDF default."""
    column_span = _table_attributes(cell).get("/ColSpan", 1)
    return int(str(column_span))


@patch.object(column_count_module, "determine_correct_column_count", return_value=4)
def test_correct_table_rows_span_different_number_columns_02(
    mock_determine: MagicMock,
):
    """Correct the corpus PDF and verify the calculated veraPDF row widths."""
    run_generic_corrector_test(
        rule_id="7.2-43",
        test_pdf_file="veraPDF_corpus/7.2-t43-fail-a.pdf",
        corrector=correct_table_rows_span_different_number_columns_02,
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
    sent_table = json.loads(table_json)

    # These are the same calculated values shown by veraPDF: rows 1 and 2
    # span four and three columns respectively.
    assert sent_table["row_widths"] == [4, 3, 4, 4, 4]
    assert sent_table["candidate_column_counts"] == [3, 4]
    assert len(sent_table["cells"]) == 16


@patch.object(column_count_module, "determine_correct_column_count", return_value=4)
def test_corrector_adds_colspan_to_the_short_row(_mock_determine: MagicMock):
    """Only the rightmost cell of the three-column row needs to be extended."""
    pdf_path = generate_resource_path("veraPDF_corpus/7.2-t43-fail-a.pdf")
    with pikepdf.open(pdf_path) as pdf:
        table = _table(pdf)
        second_row_last_header = table["/K"][1]["/K"][2]

        assert _column_span(second_row_last_header) == 1
        correct_table_rows_span_different_number_columns_02(
            _detected_violation(table), pdf
        )
        assert _column_span(second_row_last_header) == 2


@patch.object(corrector_module, "_correct_different_column_counts")
def test_corrector_delegates_to_shared_general_engine(
    mock_shared_corrector: MagicMock,
):
    """T43 must use the same fully tested grid engine as T42."""
    pdf = pikepdf.Pdf.new()
    table = pikepdf.Dictionary({"/S": pikepdf.Name("/Table")})
    violation = _detected_violation(table)

    correct_table_rows_span_different_number_columns_02(violation, pdf)

    mock_shared_corrector.assert_called_once_with(violation, pdf)
