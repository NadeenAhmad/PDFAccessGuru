import re

from pikepdf import Array, Dictionary, Name, Object, Pdf
import pikepdf

from pdfaccessguru.exceptions.mapping_exceptions.could_not_find_affected_element_exception import CouldNotFindAffectedElementException
from pdfaccessguru.exceptions.mapping_exceptions.step_function_traversal_exception import StepFunctionTraversalException
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.detect_affected_element import affected_element_detector
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.resolve_context import resolve_context_parent_element
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.resolve_context import _resolve_context
from pdfaccessguru.pipeline.reporting.writer import report_debug

from typing import Optional
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.fonts import find_font_in_context


### General information
# 
# This file contains a collection of all implemented affected_element_detectors.
#
# Feel free to add new affected_element_detectors.
##


### 
# Affected element detectors for rule_ids 5.1 to 7.1-6, Author: Aran Moradi
###

@affected_element_detector("5-1")
def detect_affected_element_5_1(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return pdf.Root.get("/Metadata")

@affected_element_detector("5-2")
def detect_affected_element_5_2(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return pdf.Root.get("/Metadata")  # the XMP metadata stream holds the PDF/UA identification

@affected_element_detector("5-3")
def detect_affected_element_5_3(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return pdf.Root.get("/Metadata")  # the XMP metadata stream holds the PDF/UA identification

@affected_element_detector("5-4")
def detect_affected_element_5_4(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return pdf.Root.get("/Metadata")  # the XMP metadata stream holds the PDF/UA identification

@affected_element_detector("5-5")
def detect_affected_element_5_5(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return pdf.Root.get("/Metadata")  # the XMP metadata stream holds the PDF/UA identification


# 6.2-1 (markinfo-dictionary-missing): VeraPDF context is "root/document[0]",
# which resolves to the whole Pdf, so the default detector would raise
# ResolveContextReturnsWholePdfException. The corrector needs the document
# catalog to add/repair the /MarkInfo dictionary, so return pdf.Root directly.
@affected_element_detector("6.2-1")
def detect_affected_element_6_2_1(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return pdf.Root


@affected_element_detector("7.1-1")
def detect_affected_element_7_1_1(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return get_page_from_context(veraPdf_violation, pdf)

@affected_element_detector("7.1-2")
def detect_affected_element_7_1_2(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return get_page_from_context(veraPdf_violation, pdf)

@affected_element_detector("7.1-4")
def detect_affected_element_7_1_4(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    mark_info = pdf.Root.get("/MarkInfo")
    return mark_info if isinstance(mark_info, Dictionary) else pdf.Root  # the dictionary holding /Suspects

@affected_element_detector("7.1-6")
def detect_affected_element_7_1_6(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    root = pdf.Root.get("/StructTreeRoot")
    role_map = root.get("/RoleMap") if isinstance(root, Dictionary) else None
    return role_map if isinstance(role_map, Dictionary) else pdf.Root

# End Aran Moradi

### 
# Affected element detectors for rule_ids 7.1-8 to 7.2-8, Author: Siju Li
###

# 7.1-7 (standard-type-remapped): context resolves cleanly to the remapped
# StructElem itself (root/document[0]/StructTreeRoot[0]/K[0]/...). The default
# step-function traversal already returns the correct affected element here,
# so no custom detector is registered for this rule_id.

# 7.1-8 (metadata-key-missing): VeraPDF context is "root/document[0]".
# The "document" segment maps to handle_root, which returns the whole Pdf
# object (not pdf.Root), and the path ends there. The default detector would
# therefore raise ResolveContextReturnsWholePdfException. The corrector
# (correct_metadata_key_missing) operates on the document catalog, so we
# return pdf.Root directly.
@affected_element_detector("7.1-8")
def detect_affected_element_7_1_8(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return pdf.Root


# 7.1-9 (missing-metadata-stream-dc-title): VeraPDF context is
# "root/document[0]/metadata[0](2 0 obj PDMetadata)/XMPPackage[0]".
# Unlike 7.1-8/10/11, this does NOT fail because the path resolves to the
# whole Pdf object - it fails earlier: RESOLVERS only registers the key
# "Metadata" (capitalized), not "metadata", so the default step-function
# traversal raises a StepFunctionTraversalException on this segment. We
# bypass resolve_context entirely. The corrector is currently a no-op (pass),
# so pdf.Root is used as the safe fallback until the real fix logic
# (targeting the XMP metadata stream / dc:title) is implemented.
@affected_element_detector("7.1-9")
def detect_affected_element_7_1_9(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    """
    VeraPDF context resolves up to 'metadata[0]', but RESOLVERS only registers
    "Metadata" (capitalized), not "metadata", so the default step function
    raises StepFunctionTraversalException. We bypass it here and access the
    metadata stream directly via pdf.Root.
    """
    metadata = pdf.Root.get("/Metadata")
    if metadata is None:
        raise CouldNotFindAffectedElementException()
    return metadata


# 7.1-10 (display-doc-title-false): VeraPDF context is just "root", which
# resolves to the whole Pdf object via handle_root and ends there, triggering
# ResolveContextReturnsWholePdfException in the default detector. The
# corrector (correct_display_doc_title_false) sets ViewerPreferences on the
# catalog, so we return pdf.Root directly.
@affected_element_detector("7.1-10")
def detect_affected_element_7_1_10(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return pdf.Root


# 7.1-11 (missing-struct-tree-root-entry): VeraPDF context is
# "root/document[0]", same situation as 7.1-8 - resolves to the whole Pdf
# object and raises ResolveContextReturnsWholePdfException. The corrector is
# currently a no-op (pass); pdf.Root is returned as the safe fallback since
# the catalog is where /StructTreeRoot would need to be added.
@affected_element_detector("7.1-11")
def detect_affected_element_7_1_11(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return pdf.Root


# 7.2-2 (natural-language-undefined): VeraPDF context is
# "root/document[0]/Outlines[0](outline ...)". handle_Outlines ignores the
# index entirely and always returns the whole /Outlines dictionary, never the
# indexed outline item - so even if the path resolved "successfully" it would
# not return what the corrector needs. correct_natural_language_undefined
# sets /Lang on the document catalog, so we return pdf.Root directly.
@affected_element_detector("7.2-2")
def detect_affected_element_7_2_2(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return pdf.Root


# 7.2-3 (table-specific-elements-missing): context resolves cleanly to the
# offending Table StructElem (root/document[0]/StructTreeRoot[0]/K[0]/K[0]).
# The default step-function traversal already returns the correct affected
# element here, so no custom detector is registered for this rule_id.

# 7.2-4 (tr-element-missing): context resolves cleanly to the misplaced TR
# StructElem itself, exactly what correct_tr_element_missing expects via
# detected_violation.affected_element. Default detector is sufficient.

# 7.2-5 (thead-element-missing): context resolves cleanly to the misplaced
# THead StructElem. Default detector is sufficient.

# 7.2-6 (tbody-element-missing): context resolves cleanly to the misplaced
# TBody StructElem. Default detector is sufficient.

# 7.2-7 (tfoot-element-missing): context resolves cleanly to the misplaced
# TFoot StructElem. Default detector is sufficient.

# 7.2-8 (th-not-contained-tr): context resolves cleanly to the misplaced TH
# StructElem. Default detector is sufficient.

# End Siju Li

### 
# Affected element detectors for rule_ids 7.2-9 to 7.2.21, Author: Robin Hart
###


@affected_element_detector("7.2-17")
def detect_affected_element_7_2_t17(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    """
    The parent of the by context resolved element is teh affected element and returned.
    """
    try :
        return resolve_context_parent_element(veraPdf_violation.context, pdf)
    except (StepFunctionTraversalException, ValueError) as e:
        raise CouldNotFindAffectedElementException from e


@affected_element_detector("7.2-18")
def detect_affected_element_7_2_t18(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    """
    The parent of the by context resolved element is teh affected element and returned.
    """
    try :
        return resolve_context_parent_element(veraPdf_violation.context, pdf)
    except (StepFunctionTraversalException, ValueError) as e:
        raise CouldNotFindAffectedElementException from e

# End Robin Hart

### 
# Affected element detectors for rule_ids 7.2-22 to 7.2-34, Author: Riard Qupevaj
###


def _extract_page_index(context: str) -> int:
    match = re.search(r"/pages\[(\d+)\]", context)
    return int(match.group(1)) if match else 0


def _extract_mcid(context: str) -> int | None:
    matches = re.findall(r"\{mcid:(\d+)\}", context)
    return int(matches[-1]) if matches else None


def _extract_metadata_objgen(context: str) -> tuple[int, int] | None:
    match = re.search(r"/metadata\[\d+\]\((\d+)\s+(\d+)\s+obj\s+PDMetadata\)", context)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def _lookup_number_tree_value(number_tree: Object, key: int) -> Object | None:
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


def _detect_struct_element_for_mcid(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    page_index = _extract_page_index(veraPdf_violation.context)
    page = pdf.pages[page_index].obj
    mcid = _extract_mcid(veraPdf_violation.context)
    if mcid is None:
        return page

    struct_parent_key = page.get("/StructParents")
    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if struct_parent_key is None or not isinstance(struct_tree_root, Dictionary):
        return page

    parent_tree = struct_tree_root.get("/ParentTree")
    parent_array = _lookup_number_tree_value(parent_tree, int(struct_parent_key))  # type: ignore
    if isinstance(parent_array, Array) and 0 <= mcid < len(parent_array):
        element = parent_array[mcid]
        if element is not None:
            return element

    return page


@affected_element_detector("7.2-33")
def detect_affected_element_7_2_33(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    metadata_objgen = _extract_metadata_objgen(veraPdf_violation.context)
    if metadata_objgen is not None:
        try:
            return pdf.get_object(metadata_objgen)
        except Exception:
            pass

    metadata = pdf.Root.get("/Metadata")
    if metadata is None:
        raise CouldNotFindAffectedElementException()
    return metadata


@affected_element_detector("7.2-30")
def detect_affected_element_7_2_30(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return _detect_struct_element_for_mcid(veraPdf_violation, pdf)


@affected_element_detector("7.2-31")
def detect_affected_element_7_2_31(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return _detect_struct_element_for_mcid(veraPdf_violation, pdf)


@affected_element_detector("7.2-32")
def detect_affected_element_7_2_32(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return _detect_struct_element_for_mcid(veraPdf_violation, pdf)


@affected_element_detector("7.2-34")
def detect_affected_element_7_2_34(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return _detect_struct_element_for_mcid(veraPdf_violation, pdf)


# End Riard Qupevaj

### 
# Affected element detectors for rule_ids 7.2-36 to 7.4.4-3, Author: Brian Karle
###




# End Brian Karle

### 
# Affected element detectors for rule_ids 7.5-1 to 7.18.1-3, Author: Florian Walcher
###

@affected_element_detector("7.5-1")
def detect_affected_element_7_5_1(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    """
    Traverses from a failing TD cell up to the TH element directly above it.
    Uses .objgen mapping to safely bypass pikepdf proxy object list index mismatches.
    """
    from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.resolve_context import _resolve_context
    import pikepdf
    try :
        td_cell = _resolve_context(veraPdf_violation.context, pdf)
    except StepFunctionTraversalException as e:
        raise CouldNotFindAffectedElementException from e

    if not td_cell or not isinstance(td_cell, pikepdf.Dictionary):
        return pdf.Root

    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if struct_tree_root:
        def find_table_context(node, target, current_tr=None, current_table=None):
            if isinstance(node, pikepdf.Array):
                for item in node:
                    res = find_table_context(item, target, current_tr, current_table)
                    if res is not None:
                        return res
            elif isinstance(node, pikepdf.Dictionary):
                tag = str(node.get("/S", ""))
                if tag == "/TR":
                    current_tr = node
                elif tag == "/Table":
                    current_table = node
                
                # Check match by comparing PDF Object/Generation numbers safely
                if hasattr(node, "objgen") and hasattr(target, "objgen") and node.objgen == target.objgen:
                    return current_tr, current_table
                
                if "/K" in node:
                    res = find_table_context(node["/K"], target, current_tr, current_table)
                    if res is not None:
                        return res
            return None

        context_res = find_table_context(struct_tree_root, td_cell)
        if context_res:
            parent_tr, parent_table = context_res
            
            if parent_tr and parent_table and "/K" in parent_tr:
                kids = parent_tr["/K"]
                if isinstance(kids, pikepdf.Array):
                    # Manual loop to find the index by matching object IDs
                    col_idx = -1
                    for idx, kid in enumerate(kids):
                        if hasattr(kid, "objgen") and kid.objgen == td_cell.objgen:
                            col_idx = idx
                            break
                    
                    if col_idx != -1 and "/K" in parent_table and isinstance(parent_table["/K"], pikepdf.Array):
                        rows = parent_table["/K"]
                        
                        # Find which row index we are currently on
                        tr_idx = -1
                        for idx, r in enumerate(rows):
                            if hasattr(r, "objgen") and r.objgen == parent_tr.objgen:
                                tr_idx = idx
                                break
                        
                        # Crawl upwards to look for the first matching header cell row
                        if tr_idx > 0:
                            for r in range(tr_idx - 1, -1, -1):
                                prev_row = rows[r]
                                if isinstance(prev_row, pikepdf.Dictionary) and "/K" in prev_row:
                                    p_kids = prev_row["/K"]
                                    if isinstance(p_kids, pikepdf.Array) and len(p_kids) > col_idx:
                                        candidate_th = p_kids[col_idx]
                                        if isinstance(candidate_th, pikepdf.Dictionary) and str(candidate_th.get("/S", "")) == "/TH":
                                            return candidate_th
                        
    return td_cell  # Fallback to the TD cell if structural hierarchy is broken


@affected_element_detector("7.5-2")
def detect_affected_element_7_5_2(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    """
    Returns the TD that references undefined header IDs (the element veraPDF reports),
    because the corrector has to clean that cell's /Headers.
    """
    try:
        element = _resolve_context(veraPdf_violation.context, pdf)
    except StepFunctionTraversalException as e:
        raise CouldNotFindAffectedElementException() from e
    if not isinstance(element, Dictionary):
        raise CouldNotFindAffectedElementException()
    return element

@affected_element_detector("7.18.1-1")
def detect_affected_element_7_18_1_1(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    """
    Finds the enclosing /StructElem for an annotation instead of returning 
    the raw annotation dictionary from the page's /Annots array.
    """
    from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.resolve_context import _resolve_context
    
    # First, use default resolver to locate the raw annotation dictionary object
    try :
        annot_obj = _resolve_context(veraPdf_violation.context, pdf)
    except StepFunctionTraversalException as e:
        raise CouldNotFindAffectedElementException from e
    if not annot_obj:
        return pdf.Root  # Safe fallback if context string completely fails
        
    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if struct_tree_root:
        def search_tree(node):
            if isinstance(node, pikepdf.Array):
                for item in node:
                    res = search_tree(item)
                    if res is not None:
                        return res
            elif isinstance(node, pikepdf.Dictionary):
                # If this is a structural element node, inspect its Kids (/K)
                if node.get("/Type") == "/StructElem" or "/S" in node:
                    kids = node.get("/K")
                    if kids is not None:
                        if isinstance(kids, pikepdf.Array):
                            for kid in kids:
                                if isinstance(kid, pikepdf.Dictionary) and kid.get("/Type") == "/OBJR" and kid.get("/Obj") == annot_obj:
                                    return node
                        elif isinstance(kids, pikepdf.Dictionary) and kids.get("/Type") == "/OBJR" and kids.get("/Obj") == annot_obj:
                            return node
                # Recurse down the structure tree hierarchy
                if "/K" in node:
                    res = search_tree(node["/K"])
                    if res is not None:
                        return res
            return None

        enclosing_struct_elem = search_tree(struct_tree_root)
        if enclosing_struct_elem is not None:
            return enclosing_struct_elem

    # Safe fallback if the PDF has no logical structure tree link for this annotation
    return annot_obj # type: ignore


@affected_element_detector("7.18.1-2")
def detect_affected_element_7_18_1_2(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    """
    Finds the enclosing /StructElem for an invalid visible annotation 
    to see if /Alt text modifications are possible at the tree element level.
    """
    # Reuse the exact same robust structural tree reverse lookup logic
    return detect_affected_element_7_18_1_1(veraPdf_violation, pdf)



# End Florian Walcher

### 
# Affected element detectors for rule_ids 7.18.2-1 to 7.21.3.2-1, Author: Marwa Ayache
###


def _find_single_reference_xobject(pdf: Pdf) -> Object:
    candidates: list[Object] = []

    for page in pdf.pages:
        page_dict = page.obj
        resources = page_dict.get("/Resources")
        if not isinstance(resources, pikepdf.Dictionary):
            continue

        xobjects = resources.get("/XObject")
        if not isinstance(xobjects, pikepdf.Dictionary):
            continue

        for xobject in xobjects.values(): # type: ignore
            if not hasattr(xobject, "get") or not hasattr(xobject, "keys"):
                continue
            if xobject.get("/Subtype") == Name("/Form") and "/Ref" in xobject:
                candidates.append(xobject)

    if len(candidates) != 1:
        raise CouldNotFindAffectedElementException()

    return candidates[0]


def _find_single_multi_referenced_form_xobject(pdf: Pdf) -> Object:
    candidates: list[Object] = []

    for page in pdf.pages:
        page_dict = page.obj
        resources = page_dict.get("/Resources")
        if not isinstance(resources, pikepdf.Dictionary):
            continue

        xobjects = resources.get("/XObject")
        if not isinstance(xobjects, pikepdf.Dictionary):
            continue

        contents = page_dict.get("/Contents")
        if contents is None or not hasattr(contents, "read_bytes"):
            continue
        page_content = contents.read_bytes().decode("latin1", errors="ignore")

        for resource_name, xobject in xobjects.items():
            if not hasattr(xobject, "get"):
                continue
            if xobject.get("/Subtype") != Name("/Form") or not hasattr(xobject, "read_bytes"):
                continue

            xobject_content = xobject.read_bytes().decode("latin1", errors="ignore")
            has_marked_content = "/MCID" in xobject_content or "BDC" in xobject_content or "BMC" in xobject_content
            if not has_marked_content:
                continue

            if page_content.count(f"{resource_name} Do") > 1:
                candidates.append(xobject)

    if len(candidates) != 1:
        raise CouldNotFindAffectedElementException()

    return candidates[0]


def _find_single_incompatible_type0_font(pdf: Pdf) -> Object:
    candidates: list[Object] = []

    for page in pdf.pages:
        page_dict = page.obj
        resources = page_dict.get("/Resources")
        if not isinstance(resources, pikepdf.Dictionary):
            continue

        fonts = resources.get("/Font")
        if not isinstance(fonts, pikepdf.Dictionary):
            continue

        for font in fonts.values(): # type: ignore
            if not isinstance(font, pikepdf.Dictionary):
                continue
            if font.get("/Subtype") != Name("/Type0"):
                continue

            descendant_fonts = font.get("/DescendantFonts")
            encoding = font.get("/Encoding")
            if not isinstance(descendant_fonts, pikepdf.Array) or len(descendant_fonts) == 0:
                continue
            if not hasattr(encoding, "get"):
                continue

            descendant_font = descendant_fonts[0]
            if not isinstance(descendant_font, pikepdf.Dictionary):
                continue

            descendant_cidsysteminfo = descendant_font.get("/CIDSystemInfo")
            encoding_cidsysteminfo = encoding.get("/CIDSystemInfo") # type: ignore
            if not isinstance(descendant_cidsysteminfo, pikepdf.Dictionary) or \
                    not isinstance(encoding_cidsysteminfo, pikepdf.Dictionary):
                continue

            for key in ["/Registry", "/Ordering", "/Supplement"]:
                if descendant_cidsysteminfo.get(key) != encoding_cidsysteminfo.get(key):
                    candidates.append(font)
                    break

    if len(candidates) != 1:
        raise CouldNotFindAffectedElementException()

    return candidates[0]


def _pdf_object_identity(obj: Object) -> tuple[str, object]:
    """Return an identity suitable for deduplicating direct and indirect objects."""
    objgen = obj.objgen
    if objgen != (0, 0):
        return "indirect", objgen
    return "direct", id(obj)


def _page_resources(page: Object) -> Object | None:
    """Return page resources, including resources inherited from the page tree."""
    page_dict = page.obj
    visited: set[tuple[str, object]] = set()

    while isinstance(page_dict, pikepdf.Dictionary):
        identity = _pdf_object_identity(page_dict)
        if identity in visited:
            return None
        visited.add(identity)

        resources = page_dict.get("/Resources")
        if isinstance(resources, pikepdf.Dictionary):
            return resources
        page_dict = page_dict.get("/Parent")

    return None


def _invalid_type_2_cidfonts_in_resources(
    resources: Object,
    visited_resources: set[tuple[str, object]],
) -> list[Object]:
    """Find invalid CIDFontType2 dictionaries in resources and nested Forms."""
    if not isinstance(resources, pikepdf.Dictionary):
        return []

    resources_identity = _pdf_object_identity(resources)
    if resources_identity in visited_resources:
        return []
    visited_resources.add(resources_identity)

    candidates: list[Object] = []
    fonts = resources.get("/Font")
    if isinstance(fonts, pikepdf.Dictionary):
        for font in fonts.values(): # type: ignore
            if not isinstance(font, pikepdf.Dictionary):
                continue

            descendant_fonts = font.get("/DescendantFonts")
            if not isinstance(descendant_fonts, pikepdf.Array):
                continue

            for descendant_font in descendant_fonts:
                if not isinstance(descendant_font, pikepdf.Dictionary):
                    continue
                if descendant_font.get("/Subtype") != Name("/CIDFontType2"):
                    continue
                if descendant_font.get("/CIDToGIDMap") != Name("/Identity"):
                    candidates.append(descendant_font)

    xobjects = resources.get("/XObject")
    if isinstance(xobjects, pikepdf.Dictionary):
        for xobject in xobjects.values(): # type: ignore
            if not isinstance(xobject, pikepdf.Stream):
                continue
            if xobject.get("/Subtype") != Name("/Form"):
                continue
            nested_resources = xobject.get("/Resources")
            if isinstance(nested_resources, pikepdf.Dictionary):
                candidates.extend(
                    _invalid_type_2_cidfonts_in_resources(
                        nested_resources,
                        visited_resources,
                    )
                )

    return candidates


def _context_page_index(context: str) -> int | None:
    match = re.search(r"(?:^|/)pages\[(\d+)]", context)
    return int(match.group(1)) if match else None


def _context_descendant_font_name(context: str) -> str | None:
    matches = re.findall(r"/DescendantFonts\[\d+]\(([^)]*)\)", context)
    if matches:
        return matches[-1]

    matches = re.findall(r"/font\[\d+]\(([^)]*)\)", context)
    return matches[-1] if matches else None


def _font_base_name(font: Object) -> str | None:
    if not isinstance(font, pikepdf.Dictionary):
        return None
    base_font = font.get("/BaseFont")
    if base_font is None:
        return None
    from pdfaccessguru.utils.pdf_names import name_text

    return name_text(base_font).removeprefix("/")


from pdfaccessguru.utils.pdf_names import same_font_name


def _find_invalid_type_2_cidfont(
    veraPdf_violation: VeraPdfViolation,
    pdf: Pdf,
) -> Object:
    """Resolve the specific invalid CIDFont reported by this veraPDF check."""
    page_index = _context_page_index(veraPdf_violation.context)
    if page_index is not None:
        if page_index >= len(pdf.pages):
            raise CouldNotFindAffectedElementException()
        pages = [pdf.pages[page_index]]
    else:
        pages = list(pdf.pages)

    candidates: list[Object] = []
    visited_resources: set[tuple[str, object]] = set()
    for page in pages:
        resources = _page_resources(page) # type: ignore
        if resources is not None:
            candidates.extend(
                _invalid_type_2_cidfonts_in_resources(
                    resources,
                    visited_resources,
                )
            )

    unique_candidates: list[Object] = []
    seen_candidates: set[tuple[str, object]] = set()
    for candidate in candidates:
        identity = _pdf_object_identity(candidate)
        if identity not in seen_candidates:
            seen_candidates.add(identity)
            unique_candidates.append(candidate)

    reported_name = _context_descendant_font_name(veraPdf_violation.context)
    if reported_name is not None:
        unique_candidates = [
            candidate
            for candidate in unique_candidates
            if same_font_name(_font_base_name(candidate), reported_name)
        ]

    if len(unique_candidates) != 1:
        raise CouldNotFindAffectedElementException()

    return unique_candidates[0]


@affected_element_detector("7.20-1")
def detect_affected_element_7_20_t01(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return _find_single_reference_xobject(pdf)


@affected_element_detector("7.20-2")
def detect_affected_element_7_20_t02(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return _find_single_multi_referenced_form_xobject(pdf)


@affected_element_detector("7.21.3.1-1")
def detect_affected_element_7_21_3_1_t01(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return _find_single_incompatible_type0_font(pdf)


@affected_element_detector("7.21.3.2-1")
def detect_affected_element_7_21_3_2_t01(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    return _find_invalid_type_2_cidfont(veraPdf_violation, pdf)


# End Marwa Ayache

### 
# Affected element detectors for rule_ids 7.21..3.3-1 to 7.21.8-1, Author: Babett Ludwig
###


# ============================================================================
# SHARED HELPER METHODS
# ============================================================================


def extract_first_word(path: str) -> Optional[str]:
    """Extracts the font name from a veraPDF context path string using font pattern matching with fallback."""
    font_pattern = r"font\[\d+\]\(([^)]+)\)"
    match = re.search(font_pattern, path)
    if match:
        return match.group(1)

    fallback_pattern = r"\(([^()\s]+)[^()]*\)$"
    match = re.search(fallback_pattern, path)
    if match:
        return match.group(1)

    return None


def normalize_basefont_name(name: Optional[str]) -> Optional[str]:
    """Strips the subset prefix (e.g., ABCDEF+FontName -> FontName) from a font name string."""
    if not name:
        return None

    if "+" in name:
        name = name.split("+", 1)[1]

    return name


def get_page_from_context(veraPdf_violation, pdf):
    """Extracts the page index from the veraPDF context string and returns the corresponding PDF page object."""
    context = veraPdf_violation.context

    match = re.search(r"pages\[(\d+)\]", context)
    if not match:
        raise Exception("Kein pages[index] im veraPDF Context gefunden")

    page_index = int(match.group(1))
    report_debug(f"DEBUG page_index: {page_index}")

    return pdf.pages[page_index]


def get_fonts_and_content_from_page(page):
    """Extracts the /Font resources and /Contents stream from a given PDF page object."""
    resources = page.obj.get("/Resources")
    if not resources:
        raise Exception("Keine /Resources gefunden")

    fonts = resources.get("/Font")
    if not fonts:
        raise Exception("Keine Fonts gefunden")

    contents = page.obj.get("/Contents")

    return fonts, contents


def find_font_by_basefont(page, base_font_name):
    """Searches a page's /Font resources and returns the font object whose /BaseFont matches the target name."""
    fonts = page.get("/Resources", {}).get("/Font", {})

    search_name = str(base_font_name).lstrip("/")

    for _, font_obj in fonts.items():
        pdf_base_font = font_obj.get("/BaseFont")

        if pdf_base_font is None:
            continue

        pdf_name = str(pdf_base_font).lstrip("/")

        if pdf_name == search_name:
            return font_obj

    return None


def find_fonts_by_basefont(container, base_font_name):
    """Recursively searches for font objects matching a base font name within resources and nested XObjects."""
    search_name = str(base_font_name).lstrip("/")

    result = []

    def search(obj):
        resources = obj.get("/Resources")

        if resources is not None:
            fonts = resources.get("/Font")

            if fonts is not None:
                for _, font_obj in fonts.items():
                    pdf_base_font = font_obj.get("/BaseFont")

                    if pdf_base_font is None:
                        continue

                    pdf_name = str(pdf_base_font).lstrip("/")

                    if pdf_name == search_name:
                        result.append(font_obj)

            xobjects = resources.get("/XObject")

            if xobjects is not None:
                for _, xobject in xobjects.items():
                    search(xobject)

    search(container)

    return result


def extract_descendant_fonts_index(context: str) -> Optional[int]:
    """Extracts the index integer from a /DescendantFonts[index] entry in a veraPDF context path."""
    match = re.search(r"/DescendantFonts\[(\d+)\]", context)

    if match:
        return int(match.group(1))

    return None


# ============================================================================
# DETECTORS: 7.21.3.3
# ============================================================================


@affected_element_detector("7.21.3.3-1")
def detect_affected_element_7_21_3_3_t01(veraPdf_violation, pdf):
    """The Type 0 font whose CMap is not embedded (rule 7.21.3.3-1)."""
    font = find_font_in_context(veraPdf_violation.context, pdf)
    if font is None:
        raise CouldNotFindAffectedElementException("No font with this name found")
    return font


@affected_element_detector("7.21.3.3-2")
def detect_affected_element_7_21_3_3_t02(veraPdf_violation, pdf):
    """The embedded CMap whose WMode differs from its dictionary (rule 7.21.3.3-2)."""
    font = find_font_in_context(veraPdf_violation.context, pdf)
    if font is None:
        raise CouldNotFindAffectedElementException("No font with this name found")
    return font.get("/Encoding")


@affected_element_detector("7.21.3.3-3")
def detect_affected_element_7_21_3_3_t03(veraPdf_violation, pdf):
    """The Type 0 font whose CMap references another non-standard CMap (rule 7.21.3.3-3)."""
    font = find_font_in_context(veraPdf_violation.context, pdf)
    if font is None:
        raise CouldNotFindAffectedElementException("No font with this name found")
    return font


@affected_element_detector("7.21.4.1-1")
def detect_affected_element_7_21_4_1_t01(veraPdf_violation, pdf):
    """The font whose program is not embedded (rule 7.21.4.1-1)."""
    font = find_font_in_context(veraPdf_violation.context, pdf)
    if font is None:
        return pdf.Root          # the fix covers every font of the document anyway
    return font


@affected_element_detector("7.21.4.2-1")
def detect_affected_element_7_21_4_2_t01(veraPdf_violation, pdf):
    """Detects and returns the affected Type 1 font object for rule 7.21.4.2-1."""
    page = get_page_from_context(veraPdf_violation, pdf)
    base_font_veraPDF = extract_first_word(veraPdf_violation.context)
    font_obj = find_font_by_basefont(page.obj, base_font_veraPDF)
    if font_obj is None:
        raise CouldNotFindAffectedElementException(
            "No font obj found"
        )
    return font_obj


@affected_element_detector("7.21.4.2-2")
def detect_affected_element_7_21_4_2_t02(veraPdf_violation, pdf):
    """Detects and returns the affected font descriptor dictionary containing an invalid CIDSet for rule 7.21.4.2-2."""
    page = get_page_from_context(veraPdf_violation, pdf)
    context = veraPdf_violation.context
    base_font_veraPDF = extract_first_word(context)
    descendant_font_index = extract_descendant_fonts_index(context)

    if descendant_font_index is None:
        raise CouldNotFindAffectedElementException(
            "No DescendantFont index found"
        )

    if "/xObject[" not in context:
        font_objs = find_fonts_by_basefont(
            page.obj, base_font_veraPDF
        )
    else:
        font_objs = find_font_from_xobject_context(
            page, pdf, context, base_font_veraPDF
        )

    for font_obj in font_objs:
        descendant_fonts = font_obj.get("/DescendantFonts")

        if descendant_fonts is None:
            continue

        if descendant_font_index >= len(descendant_fonts):
            continue

        descendant_font = descendant_fonts[descendant_font_index]

        if descendant_font is None:
            continue

        font_descriptor = descendant_font.get("/FontDescriptor")

        if font_descriptor is None:
            continue

        if "/CIDSet" not in font_descriptor:
            raise CouldNotFindAffectedElementException(
                "No font descriptor with CIDSet found"
            )

        return font_descriptor

    raise CouldNotFindAffectedElementException(
        "No FontDescriptor with CIDSet found"
    )


# ============================================================================
# DETECTORS: 7.21.5 AND 7.21.6
# ============================================================================


@affected_element_detector("7.21.5-1")
def detect_affected_element_7_21_5_t01(veraPdf_violation, pdf):
    """The font whose widths differ from its program (rule 7.21.5-1)."""
    font = find_font_in_context(veraPdf_violation.context, pdf)
    if font is None:
        return pdf.Root          # the fix covers every font of the document anyway
    return font


@affected_element_detector("7.21.6-1")
def detect_affected_element_7_21_6_t01(veraPdf_violation, pdf):
    """The non-symbolic TrueType font without a Unicode character table (rule 7.21.6-1)."""
    font = find_font_in_context(veraPdf_violation.context, pdf)
    if font is None:
        return pdf.Root          # the fix covers every font of the document anyway
    return font


@affected_element_detector("7.21.6-2")
def detect_affected_element_7_21_6_t02(veraPdf_violation, pdf):
    """Detects and returns the affected non-symbolic TrueType font object for rule 7.21.6-2."""
    page = get_page_from_context(veraPdf_violation, pdf)
    base_font_veraPDF = extract_first_word(veraPdf_violation.context)
    font_obj = find_font_by_basefont(page, base_font_veraPDF)
    if font_obj is None:
        raise CouldNotFindAffectedElementException(
            "No font_obj found"
        )
    return font_obj


@affected_element_detector("7.21.6-3")
def detect_affected_element_7_21_6_t03(veraPdf_violation, pdf):
    """Detects and returns the affected symbolic TrueType font object for rule 7.21.6-3."""
    page = get_page_from_context(veraPdf_violation, pdf)
    base_font_veraPDF = extract_first_word(veraPdf_violation.context)
    font_obj = find_font_by_basefont(page, base_font_veraPDF)
    if font_obj is None:
        raise CouldNotFindAffectedElementException(
            "No font_obj found"
        )

    return font_obj


@affected_element_detector("7.21.6-4")
def detect_affected_element_7_21_6_t04(veraPdf_violation, pdf):
    """The symbolic TrueType font whose program lacks the (3,0) character table (rule 7.21.6-4)."""
    font = find_font_in_context(veraPdf_violation.context, pdf)
    if font is None:
        return pdf.Root          # the fix covers every font of the document anyway
    return font


# ============================================================================
# DETECTORS: 7.21.7 AND 7.21.8
# ============================================================================



@affected_element_detector("7.21.7-1")
def detect_affected_element_7_21_7_t01(veraPdf_violation, pdf):
    """Detects and returns the /Contents stream of the page containing unmapped Unicode characters for rule 7.21.7-1."""
    page = get_page_from_context(veraPdf_violation, pdf)
    contents = page.obj.get("/Contents")

    report_debug(f"DEBUG contents: {contents}")

    if not contents:
        return None

    return contents


@affected_element_detector("7.21.7-2")
def detect_affected_element_7_21_7_t02(veraPdf_violation, pdf):
    """Detects and returns the /ToUnicode CMap stream containing invalid Unicode mappings for rule 7.21.7-2."""
    page = get_page_from_context(veraPdf_violation, pdf)
    fonts, contents = get_fonts_and_content_from_page(page)
    report_debug(f"DEBUG contents: {contents}")
    base_font_veraPDF = extract_first_word(veraPdf_violation.context)
    font_obj = find_font_by_basefont(page, base_font_veraPDF)
    to_unicode = font_obj.get("/ToUnicode")
    return to_unicode


@affected_element_detector("7.21.8-1")
def detect_affected_element_7_21_8_t01(veraPdf_violation, pdf):
    """Detects and returns the affected page object for rule 7.21.8-1."""
    page = get_page_from_context(veraPdf_violation, pdf)

    report_debug(f"DEBUG affected page: {page}")

    return page