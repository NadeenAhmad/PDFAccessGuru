import importlib
from typing import Callable, cast

from pikepdf import Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


# Rules 7.2-42 and 7.2-43 require the same logical grid repair. Reusing the
# tested implementation keeps RoleMap, RowSpan and safety behavior identical.
_COLUMN_COUNT_CORRECTOR_MODULE = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax."
    "syntax_correctors_5_brian_karle.7_2_t42_table_rows_span_different_number_columns"
)
_correct_different_column_counts = cast(
    Callable[[DetectedViolation, Pdf], None],
    getattr(
        _COLUMN_COUNT_CORRECTOR_MODULE,
        "correct_table_rows_span_different_number_columns",
    ),
)


@corrector("table-rows-span-different-number-columns-02")
def correct_table_rows_span_different_number_columns_02(
    detected_violation: DetectedViolation,
    pdf: Pdf,
) -> None:
    """
    Correct veraPDF rule 7.2-43.

    veraPDF reports the calculated column counts of the compared rows for this
    rule. Those values are not retained by the current DetectedViolation model,
    so the shared correction engine recalculates every row width directly from
    the PDF structure, including /RowSpan and /ColSpan. It then gives the full
    table and calculated values to the LLM, validates its choice, simulates the
    correction and finally writes only safe /ColSpan changes.
    """
    # Delegate to the general column-count engine used by the equivalent T42 rule.
    _correct_different_column_counts(detected_violation, pdf)
