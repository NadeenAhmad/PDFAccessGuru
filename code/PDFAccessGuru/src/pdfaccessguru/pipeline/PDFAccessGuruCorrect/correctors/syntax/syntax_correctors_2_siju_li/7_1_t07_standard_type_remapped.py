from pikepdf import Dictionary, Name, Pdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.language_utils import (
    extract_text_for_struct_element,
)

# The 17 standard structure types per ISO 32000-1:2008, 14.8.4, Table 333/337/etc.
STANDARD_TYPES = {
    "Document", "Part", "Div", "Caption", "THead", "TBody", "TFoot",
    "TR", "TH", "TD", "Table", "L", "LI", "Lbl", "LBody",
    "P", "H", "H1", "H2", "H3", "H4", "H5", "H6",
    "Span", "Quote", "Note", "Reference", "BibEntry", "Code",
    "Link", "Annot", "Ruby", "RB", "RT", "RP", "Warichu", "WT", "WP",
    "Figure", "Formula", "Form", "Artifact",
}
DEFAULT_FALLBACK_TYPE = "Div"


@corrector("standard-type-remapped")
def correct_standard_type_remapped(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.1-7

    Violation: a standard structure type (e.g. /P) is remapped in /RoleMap, which
    ISO 32000-1:2008, 14.8.4 forbids. The affected element carries this standard type as /S.

    Fix: the illegal /RoleMap entry is removed. The element keeps the standard type its
    author gave it, which is then interpreted with its standard meaning. (Earlier versions
    let a language model retype every such element, which could turn paragraphs into
    headings or tables into paragraphs.)
    """
    element = detected_violation.affected_element
    if not isinstance(element, Dictionary):
        raise CouldNotCorrectDetectedViolationException("standard-type-remapped")

    remapped_type = str(element.get("/S", "")).lstrip("/")
    if not remapped_type:
        raise CouldNotCorrectDetectedViolationException("standard-type-remapped")

    _remove_illegal_rolemap_entry(pdf, remapped_type)


def _remove_illegal_rolemap_entry(pdf: Pdf, remapped_type: str) -> None:
    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if struct_tree_root is None:
        return

    role_map = struct_tree_root.get("/RoleMap")
    if not isinstance(role_map, Dictionary):
        return

    key = f"/{remapped_type}"
    if key in role_map:
        del role_map[key]