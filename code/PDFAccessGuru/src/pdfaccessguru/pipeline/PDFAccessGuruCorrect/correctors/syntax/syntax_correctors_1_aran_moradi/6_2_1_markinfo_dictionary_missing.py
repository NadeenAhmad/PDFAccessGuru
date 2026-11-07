from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pikepdf import Dictionary, Pdf
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi.constants import (
    PDFUA_NAMESPACE,
    RDF_NAMESPACE,
    STANDARD_TYPES,
)
from lxml import etree
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException


@corrector("markinfo-dictionary-missing")
def correct_markinfo_dictionary_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 6.2-1
    Violation description: MarkInfo dictionary is not present in the document catalog,
    or Marked entry is set to false or is not present in the MarkInfo dictionary
    Correction strategy:
    The document catalog is the affected element. A MarkInfo dictionary with
    Marked set to true is created, or an existing one has its Marked entry set to true.
    Before correction:
    ...|
       |_/Catalog (no /MarkInfo or /Marked false)
    After correction:
    ...|
       |_/Catalog|
                  |_/MarkInfo|
                             |_/Marked true

    Marked is only set when the document really has a structure tree with content.
    For an untagged document, Marked=true would tell assistive technology to rely on an
    empty or missing tree, so screen readers would find no content at all.
    """
    affected_element = detected_violation.affected_element

    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(struct_tree_root, Dictionary) or not struct_tree_root.get("/K"):
        raise CouldNotCorrectDetectedViolationException(
            "markinfo-dictionary-missing: the document has no structure tree with content, "
            "so it must be tagged before it can be marked as tagged"
        )

    if "/MarkInfo" not in affected_element:
        affected_element["/MarkInfo"] = Dictionary(Marked=True)
    else:
        affected_element["/MarkInfo"]["/Marked"] = True