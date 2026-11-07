import pikepdf
from pikepdf import Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_6_florian_walcher.table_headers import (
    assign_header_scopes,
    find_table,
    header_ids,
)


def _drop_undefined_ids(container: pikepdf.Dictionary, valid_ids: set[bytes]) -> int:
    """Remove header IDs that no TH of the table defines. Returns how many were removed."""
    headers = container.get("/Headers")
    if not isinstance(headers, pikepdf.Array):
        return 0
    kept = [header for header in headers if bytes(header) in valid_ids]
    removed = len(headers) - len(kept)
    if kept:
        container["/Headers"] = pikepdf.Array(kept)
    else:
        del container["/Headers"]
    return removed


@corrector("td-undefined-headers")
def correct_td_undefined_headers(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.5-2
    Violation description: a TD references header IDs that are not defined, and its
    headers cannot be determined algorithmically.

    Correction strategy:
    Only the undefined IDs are removed from the TD's /Headers (in the element and in its
    /Table attribute dictionaries); valid IDs are kept. Header cells without a /Scope then
    get one from their position, as for rule 7.5-1.
    """
    cell = detected_violation.affected_element
    if not isinstance(cell, pikepdf.Dictionary) or str(cell.get("/S", "")) != "/TD":
        raise CouldNotCorrectDetectedViolationException("td-undefined-headers: affected element is not a TD")

    table = find_table(cell)
    if table is None:
        raise CouldNotCorrectDetectedViolationException("td-undefined-headers: no enclosing table found")

    valid_ids = header_ids(table)
    _drop_undefined_ids(cell, valid_ids)
    attributes = cell.get("/A")
    for attribute in attributes if isinstance(attributes, pikepdf.Array) else [attributes]:
        if isinstance(attribute, pikepdf.Dictionary):
            _drop_undefined_ids(attribute, valid_ids)

    assign_header_scopes(table)
