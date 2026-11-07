from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pikepdf import Array, Dictionary, Name, Object, Pdf
import pikepdf
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi.constants import (
    PDFUA_NAMESPACE,
    RDF_NAMESPACE,
    STANDARD_TYPES,
)
from lxml import etree
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException


def _lookup_number_tree_value(number_tree, key: int):
    """
    Resolve a value in a PDF number tree (walks /Nums, recurses into /Kids),
    e.g. StructTreeRoot's /ParentTree. Mirrors the same lookup already used on
    the detect side (detect_affected_element/registry.py's
    _lookup_number_tree_value); duplicated locally so this corrector stays
    self-contained, matching the convention of every other file in this
    package.
    """
    if not isinstance(number_tree, Dictionary):
        return None

    nums = number_tree.get("/Nums")
    if isinstance(nums, Array):
        for index in range(0, len(nums), 2):
            if int(nums[index]) == key:
                return nums[index + 1]

    kids = number_tree.get("/Kids")
    if isinstance(kids, Array):
        for kid in kids:
            value = _lookup_number_tree_value(kid, key)
            if value is not None:
                return value

    return None


def _struct_elem_for_mcid(pdf: Pdf, page: Object, mcid: int):
    """
    Return the StructElem the structure tree actually links to this page's
    MCID, or None if the MCID is not referenced anywhere (orphaned).
    """
    struct_parent_key = page.get("/StructParents")
    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if struct_parent_key is None or not isinstance(struct_tree_root, Dictionary):
        return None

    parent_tree = struct_tree_root.get("/ParentTree")
    parent_array = _lookup_number_tree_value(parent_tree, int(struct_parent_key))
    if isinstance(parent_array, Array) and 0 <= mcid < len(parent_array):
        return parent_array[mcid]
    return None


def _fix_artifact_mcid_hybrids(pdf: Pdf, page: Object, instructions):
    """
    Fix marked-content blocks that are simultaneously tagged /Artifact and
    carry an /MCID (invalid by construction: an Artifact should never link
    into the structure tree). If the MCID is genuinely referenced by a
    StructElem, the Artifact classification is the mistake, so the block is
    retagged with the StructElem's own /S type (falling back to /P). If the
    MCID is not referenced anywhere, it is orphaned and safe to drop, keeping
    the block a clean, unambiguous Artifact.
    Returns whether anything changed.
    """
    changed = False
    for operands, operator in instructions:
        if str(operator) not in ("BDC", "BMC"):
            continue
        if not operands or str(operands[0]) != "/Artifact":
            continue
        if len(operands) < 2 or not isinstance(operands[-1], Dictionary):
            continue
        properties = operands[-1]
        if "/MCID" not in properties:
            continue

        mcid = int(properties["/MCID"])
        struct_elem = _struct_elem_for_mcid(pdf, page, mcid)
        if struct_elem is not None:
            standard_type = struct_elem.get("/S")
            operands[0] = Name(str(standard_type)) if standard_type is not None else Name("/P")
        else:
            del properties["/MCID"]
        changed = True

    return changed


@corrector("artifact-present-inside-tagged-content")
def correct_artifact_present_inside_tagged_content(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.1-1
    Violation description: Content marked as Artifact is present inside tagged content
    Correction strategy:
    Two distinct shapes are handled.
    1. Physical nesting: an Artifact marked-content sequence is nested inside a
       tagged BDC/EMC block. The nested Artifact BDC and its matching EMC are
       unwrapped, leaving the surrounding tagged content intact.
       Before correction:
       BDC /P <</MCID n>>
           BMC /Artifact
               ...
           EMC
       EMC
       After correction:
       BDC /P <</MCID n>>
           ...
       EMC
    2. Self-contradictory single block: a BDC/BMC tagged /Artifact that also
       carries an /MCID (an Artifact should never link into the structure
       tree). If that MCID is genuinely referenced by a StructElem, the block
       is retagged with the StructElem's own type (falling back to /P); if the
       MCID is orphaned (not referenced anywhere), it is simply dropped from
       the Artifact's properties.
       Before correction:
       BDC /Artifact <</MCID 91>>
           ...
       EMC
       After correction (MCID referenced by a /P StructElem):
       BDC /P <</MCID 91>>
           ...
       EMC
       After correction (MCID orphaned):
       BDC /Artifact
           ...
       EMC

    Known limitation:
    If the document has no /StructTreeRoot or /ParentTree at all, the MCID
    lookup in step 2 cannot find a referencing StructElem and the block is
    treated as orphaned (its /MCID is dropped) even if it was meant to be
    real content — repairing a missing structure tree is out of scope here.
    """
    affected_element = detected_violation.affected_element

    try:
        instructions = list(pikepdf.parse_content_stream(affected_element))
    except Exception as e:
        raise CouldNotCorrectDetectedViolationException("artifact-present-inside-tagged-content") from e

    corrected_instructions = []
    inside_tagged_content = False
    skip_nested_artifact = False

    for operands, operator in instructions:
        operator_name = str(operator)

        if operator_name == "BDC":
            if inside_tagged_content and operands and str(operands[0]) == "/Artifact":
                skip_nested_artifact = True
                continue
            inside_tagged_content = True
        elif operator_name == "BMC":
            if inside_tagged_content and operands and str(operands[0]) == "/Artifact":
                skip_nested_artifact = True
                continue
            inside_tagged_content = True
        elif operator_name == "EMC":
            if skip_nested_artifact:
                skip_nested_artifact = False
                continue
            inside_tagged_content = False

        corrected_instructions.append((operands, operator))

    _fix_artifact_mcid_hybrids(pdf, affected_element, corrected_instructions)

    affected_element["/Contents"] = pdf.make_stream(
        pikepdf.unparse_content_stream(corrected_instructions)
    )