from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.table_headers import (
    assign_header_scopes,
    find_table,
)


@corrector("td-headers-missing")
def correct_td_headers_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.5-1

    Violation description:
    The headers of a table cell cannot be determined: header cells (TH) have no /Scope
    and data cells have no /Headers.

    Correction strategy:
    The enclosing /Table is located from the affected cell (TH or TD). Every header cell
    without a /Scope gets one derived from its position (see table_headers.py):
    first row or THead -> /Column, first cell of a later row -> /Row. Existing scopes and
    /Headers entries are kept.

    Not corrected (reported instead):
    - tables without any TH: which cells are headers is a content decision that has to be
      made by tagging, not guessed here;
    - tables where some header cells stay ambiguous (TH in the middle of a row).
    """
    table = find_table(detected_violation.affected_element)
    if table is None:
        raise CouldNotCorrectDetectedViolationException("td-headers-missing: no enclosing table found")

    header_cells, _, ambiguous = assign_header_scopes(table)
    if header_cells == 0:
        raise CouldNotCorrectDetectedViolationException(
            "td-headers-missing: the table has no header cells (TH); headers must be marked first"
        )
    if ambiguous:
        raise CouldNotCorrectDetectedViolationException(
            f"td-headers-missing: {ambiguous} header cell(s) are neither in the first row nor the first column"
        )
