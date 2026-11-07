


import os
from pathlib import Path
from typing import Callable, Any
from dataclasses import dataclass

import pikepdf
from pikepdf import Name, Object, Page, ContentStreamInstruction, Array, Dictionary, String
from pikepdf import parse_content_stream as pikepdf_parse_content_stream

from pdfaccessguru.exceptions.mapping_exceptions.could_not_find_affected_element_exception import CouldNotFindAffectedElementException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.reporting.writer import report_debug
import re
from typing import Optional

from pdfaccessguru.model.supplementary_information.supplementary_information import (
    AnnotationStructureContextSupplementaryInformation,
    LanguageContextSupplementaryInformation,
    SupplementaryInformation,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collect_supplementary_information import (
    supplementary_information_collector,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.utils.structure_tree_helpers import (
    find_objr_parent_for_annotation,
    find_parent_of_struct_element,
)


'''
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig import (
    correct_font_program_embedded,
)
'''

from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.taxonomy_data_mapping.map_verapdf_violation_to_taxonomy_data import (
    map_rule_id_to_syntax_violation_name,
)

from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf




### General information
# 
# This file contains a collection of all implemented supplementary_information_collectors.
#
# Feel free to add new supplementary_information_collector.
##


### 
# Supplementary information collectors for rule_ids 7.5-7 to 7.18.1-3, Author: Aran Moradi
###




# End Aran Moradi

### 
# Supplementary information collectors for rule_ids 7.5-7 to 7.18.1-3, Author: Siju Li
###




# End Siju Li

### 
# Supplementary information collectors for rule_ids 7.5-7 to 7.18.1-3, Author: Robin Hart
###

# See in extra folder collectors_3_robin_hart

# End Robin Hart

### 
# Supplementary information collectors for rule_ids 7.5-7 to 7.18.1-3, Author: Riard Qupevaj
###




# End Riard Qupevaj

### 
# Supplementary information collectors for rule_ids 7.5-7 to 7.18.1-3, Author: Brian Karle
###




# End Brian Karle

### 
# Supplementary information collectors for rule_ids 7.5-7 to 7.18.1-3, Author: Florian Walcher
###




# End Florian Walcher

### 
# Supplementary information collectors for rule_ids 7.5-7 to 7.18.1-3, Author: Marwa Ayache
###


DEFAULT_ALT_LANGUAGE = "en-US"
_AVAILABLE_LOCALE_TAGS: set[str] | None = None


def _available_locale_tags() -> set[str]:
    global _AVAILABLE_LOCALE_TAGS
    if _AVAILABLE_LOCALE_TAGS is not None:
        return _AVAILABLE_LOCALE_TAGS

    import json

    locales_path = Path(__file__).resolve().parents[4] / "LLM" / "material" / "availableLocales.json"
    with locales_path.open(encoding="utf-8") as locales_file:
        locales = json.load(locales_file)

    _AVAILABLE_LOCALE_TAGS = set(locales.get("availableLocales", {}).get("full", []))
    return _AVAILABLE_LOCALE_TAGS


def _normalize_valid_language_tag(language: object) -> str | None:
    if language is None:
        return None

    language_tag = str(language).strip()
    if language_tag in _available_locale_tags():
        return language_tag

    return None


def _is_same_pdf_object(left: object, right: object) -> bool:
    left_objgen = getattr(left, "objgen", None)
    right_objgen = getattr(right, "objgen", None)
    if left_objgen is not None and right_objgen is not None:
        return left_objgen == right_objgen

    try:
        return left is right or left == right
    except Exception:
        return False


def _annotation_media_clip_data_matches(annotation: object, media_clip_data: object) -> bool:
    if not isinstance(annotation, Dictionary):
        return False

    action = annotation.get("/A")
    if not isinstance(action, Dictionary):
        return False

    rendition = action.get("/R")
    if not isinstance(rendition, Dictionary):
        return False

    annotation_media_clip_data = rendition.get("/C")
    if annotation_media_clip_data is None:
        return False

    return _is_same_pdf_object(annotation_media_clip_data, media_clip_data)


def _find_page_for_media_clip_data(pdf: pikepdf.Pdf, media_clip_data: Object) -> Object | None:
    for page in pdf.pages:
        page_object = page.obj
        annotations = page_object.get("/Annots")
        if not isinstance(annotations, Array):
            continue

        for annotation in annotations:
            if _annotation_media_clip_data_matches(annotation, media_clip_data):
                return page_object

    return None


def _collect_media_clip_language_context(pdf: pikepdf.Pdf, affected_element: Object) -> list[SupplementaryInformation]:
    page = _find_page_for_media_clip_data(pdf, affected_element)
    if isinstance(page, Dictionary):
        page_language = _normalize_valid_language_tag(page.get("/Lang"))
        if page_language is not None:
            return [LanguageContextSupplementaryInformation(page_language, "page")]

    document_language = _normalize_valid_language_tag(pdf.Root.get("/Lang"))
    if document_language is not None:
        return [LanguageContextSupplementaryInformation(document_language, "document")]

    return [LanguageContextSupplementaryInformation(DEFAULT_ALT_LANGUAGE, "default")]


def _collect_annotation_structure_context(pdf, affected_element) -> list[SupplementaryInformation]:
    if not isinstance(affected_element, Dictionary):
        return []

    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(struct_tree_root, Dictionary):
        return []

    root_kids = struct_tree_root.get("/K")
    search_roots = []
    if isinstance(root_kids, Dictionary):
        search_roots = [root_kids]
    elif isinstance(root_kids, pikepdf.Array):
        search_roots = [child for child in root_kids if isinstance(child, Dictionary)]

    match = None
    for root in search_roots:
        match = find_objr_parent_for_annotation(root, affected_element)
        if match is not None:
            break

    if match is None:
        return []

    objr_parent, objr_index, objr_dict = match
    parent_match = None
    for root in search_roots:
        parent_match = find_parent_of_struct_element(root, objr_parent)
        if parent_match is not None:
            break

    objr_parent_parent = None
    objr_parent_parent_index = None
    if parent_match is not None:
        objr_parent_parent, objr_parent_parent_index = parent_match

    return [AnnotationStructureContextSupplementaryInformation(
        objr_parent=objr_parent,
        objr_index=objr_index,
        objr_dict=objr_dict,
        objr_parent_parent=objr_parent_parent,
        objr_parent_parent_index=objr_parent_parent_index,
    )]


@supplementary_information_collector("7.18.4-1")
def collect_supplementary_information_7_18_4_1(veraPdf_violation, pdf, affected_element) -> list[SupplementaryInformation]:
    return _collect_annotation_structure_context(pdf, affected_element)


@supplementary_information_collector("7.18.5-1")
def collect_supplementary_information_7_18_5_1(veraPdf_violation, pdf, affected_element) -> list[SupplementaryInformation]:
    return _collect_annotation_structure_context(pdf, affected_element)


@supplementary_information_collector("7.18.8-1")
def collect_supplementary_information_7_18_8_1(veraPdf_violation, pdf, affected_element) -> list[SupplementaryInformation]:
    return _collect_annotation_structure_context(pdf, affected_element)


@supplementary_information_collector("7.18.6.2-2")
def collect_supplementary_information_7_18_6_2_2(veraPdf_violation, pdf, affected_element) -> list[SupplementaryInformation]:
    return _collect_media_clip_language_context(pdf, affected_element)




# End Marwa Ayache

### 
# Supplementary information collectors for rule_ids 7.5-7 to 7.18.1-3, Author: Babett Ludwig
###

# helper methods

def extract_first_word(path: str) -> Optional[str]:
    """Extracts the font name or last target identifier from a veraPDF context path string."""
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
    """Strips the subset prefix (e.g. ABCDEF+FontName -> FontName) from a PDF base font name."""
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


def find_font_by_basefont(page, base_font_name) -> Optional[Object]:
    """Extracts the matching PDF font object from a page's resource dictionary by comparing base font names."""
    resources = page.get("/Resources")
    if not resources:
        return None
    fonts = resources.get("/Font")
    if not fonts:
        return None

    search_name = normalize_basefont_name(base_font_name)
    if search_name is None:
        return None

    for font_key, font_obj in fonts.items():
        base_font_pdf = font_obj.get("/BaseFont")
        if base_font_pdf is None:
            continue
        pdf_name = normalize_basefont_name(str(base_font_pdf).lstrip("/"))
        if pdf_name == search_name:
            return font_obj
    return None


def extract_operator_and_glyph_index(context: str):
    """Extracts operator and glyph indices from a veraPDF context path string."""
    op_match = re.search(r"/operators\[(\d+)\]", context)
    glyph_match = re.search(r"/usedGlyphs\[(\d+)\]", context)

    operator_index = int(op_match.group(1)) if op_match else None
    glyph_index = int(glyph_match.group(1)) if glyph_match else None

    return operator_index, glyph_index


def parse_content_stream(page_or_stream) -> list:
    """Parses and returns content stream instructions from a page or stream object."""
    if hasattr(page_or_stream, "obj"):
        page_or_stream = page_or_stream.obj
    return pikepdf_parse_content_stream(page_or_stream)


def extract_used_codes_for_font_across_pdf(
    pdf: pikepdf.Pdf, target_font_obj: pikepdf.Object
) -> set[int]:
    """Extracts all character codes referenced across all PDF page content streams for a given font object."""
    result: set[int] = set()

    for page in pdf.pages:
        page_obj = page.obj

        resources = page_obj.get("/Resources")
        if not resources:
            continue

        fonts = resources.get("/Font", {})
        if not fonts:
            continue

        target_font_key = None
        for key, value in fonts.items():
            if value == target_font_obj:
                target_font_key = str(key).lstrip("/")
                break

        if target_font_key is None:
            continue

        instructions = parse_content_stream(page_obj)
        current_font = None

        byte_width = (
            2 if target_font_obj.get("/Subtype") == Name.Type0 else 1
        )

        for instr in instructions:
            op = str(instr.operator)
            operands = instr.operands

            if op == "Tf" and len(operands) >= 2:
                current_font = str(operands[0]).lstrip("/")

            elif op in ("Tj", "'", '"') and operands:
                if current_font == target_font_key and isinstance(
                    operands[-1], pikepdf.String
                ):
                    raw = bytes(operands[-1])
                    for i in range(0, len(raw), byte_width):
                        result.add(
                            int.from_bytes(
                                raw[i : i + byte_width], "big"
                            )
                        )

            elif op == "TJ" and operands:
                if current_font == target_font_key:
                    for el in operands[0]:
                        if isinstance(el, pikepdf.String):
                            raw = bytes(el)
                            for i in range(0, len(raw), byte_width):
                                result.add(
                                    int.from_bytes(
                                        raw[i : i + byte_width], "big"
                                    )
                                )

    return result





@supplementary_information_collector("7.21.8-1")
def collect_supplementary_information_7_21_8_1(
    veraPdf_violation, pdf, affected_element
) -> list:
    """Extracts raw page dictionary, ToUnicode stream, operator index, and glyph index for rule 7.21.8-1."""
    page = get_page_from_context(veraPdf_violation, pdf)
    page_raw = page.obj
    base_font_veraPDF = extract_first_word(veraPdf_violation.context)
    font_obj = find_font_by_basefont(page, base_font_veraPDF)
    to_unicode = font_obj.get("/ToUnicode")
    operator_index, glyph_index = extract_operator_and_glyph_index(
        veraPdf_violation.context
    )

    return [page_raw, to_unicode, operator_index, glyph_index]



# COLLECTOR: 7.21.4.1-1 and helper methods

def find_font_in_page_xobjects(page_obj, base_font_name: str):
    """Extracts font object and Form XObject from page resources matching the given base font name."""
    resources = page_obj.get("/Resources")

    if not resources:
        return None, None

    xobjects = resources.get("/XObject")

    if not xobjects:
        return None, None

    for xobject_name, xobject in xobjects.items():
        if xobject.get("/Subtype") != pikepdf.Name("/Form"):
            continue

        xobject_resources = xobject.get("/Resources")

        if not xobject_resources:
            continue

        fonts = xobject_resources.get("/Font")

        if not fonts:
            continue

        for font_name, font_obj in fonts.items():
            current_base_font = str(
                font_obj.get("/BaseFont", "")
            ).lstrip("/")

            if current_base_font == base_font_name:
                return font_obj, xobject

    return None, None


def extract_used_codes_for_xobject_font(
    xobject, target_font_obj
) -> set[int]:
    """Extracts character codes used within a specific Form XObject content stream for a given font object."""
    result = set()

    resources = xobject.get("/Resources")

    if not resources:
        return result

    fonts = resources.get("/Font")

    if not fonts:
        return result

    target_font_key = None

    for key, value in fonts.items():
        if value == target_font_obj:
            target_font_key = str(key).lstrip("/")
            break

    if target_font_key is None:
        return result

    instructions = parse_content_stream(xobject)

    current_font = None

    subtype = target_font_obj.get("/Subtype")

    byte_width = 2 if subtype == pikepdf.Name("/Type0") else 1

    for index, instr in enumerate(instructions):
        op = str(instr.operator)
        operands = instr.operands

        if op == "Tf" and len(operands) >= 2:
            current_font = str(operands[0]).lstrip("/")

        elif op in ("Tj", "'", '"') and operands:
            if current_font == target_font_key and isinstance(
                operands[-1], pikepdf.String
            ):
                raw = bytes(operands[-1])

                for i in range(0, len(raw), byte_width):
                    chunk = raw[i : i + byte_width]

                    if len(chunk) == byte_width:
                        code = int.from_bytes(chunk, "big")
                        result.add(code)

        elif op == "TJ" and operands:
            if current_font == target_font_key:
                for element in operands[0]:
                    if not isinstance(element, pikepdf.String):
                        continue

                    raw = bytes(element)

                    for i in range(0, len(raw), byte_width):
                        chunk = raw[i : i + byte_width]

                        if len(chunk) == byte_width:
                            code = int.from_bytes(chunk, "big")
                            result.add(code)

    return result


def extract_xobject_indices(context: str) -> list[int]:
    """Extracts all xObject indices from a veraPDF context string."""
    return [int(x) for x in re.findall(r"/xObject\[(\d+)\]", context)]


def get_all_page_xobjects(page_obj):
    """Extracts all top-level XObjects directly defined in page resources."""
    resources = page_obj.get("/Resources")

    if not resources:
        return []

    xobjects = resources.get("/XObject")

    if not xobjects:
        return []

    result = []

    for name, xobject in xobjects.items():
        result.append((str(name).lstrip("/"), xobject))

    return result


def get_xobject_from_operator(page_obj, operator_index: int):
    """Extracts the XObject referenced by a 'Do' operator at a specific operator index."""
    instructions = parse_content_stream(page_obj)

    if operator_index >= len(instructions):
        return None

    instr = instructions[operator_index]

    if str(instr.operator) != "Do":
        return None

    if not instr.operands:
        return None

    xobject_name = str(instr.operands[0]).lstrip("/")

    resources = page_obj.get("/Resources")

    if not resources:
        return None

    xobjects = resources.get("/XObject")

    if not xobjects:
        return None

    for key, xobj in xobjects.items():
        if str(key).lstrip("/") == xobject_name:
            return xobj

    return None


def find_font_by_basefont_recursive(
    page_obj: pikepdf.Dictionary, base_font_name: str
):
    """Extracts font object recursively traversing nested Form XObject resource dictionaries."""
    visited = set()

    def search_resources(resources):
        if not resources:
            return None

        fonts = resources.get("/Font")
        if fonts:
            for _, font_obj in fonts.items():
                try:
                    base_font = str(
                        font_obj.get("/BaseFont", "")
                    ).lstrip("/")
                except Exception:
                    continue

                if base_font == base_font_name:
                    return font_obj

        xobjects = resources.get("/XObject")
        if not xobjects:
            return None

        for _, xobj in xobjects.items():
            try:
                objgen = xobj.objgen
            except Exception:
                objgen = id(xobj)

            if objgen in visited:
                continue

            visited.add(objgen)

            if xobj.get("/Subtype") != pikepdf.Name("/Form"):
                continue

            child_resources = xobj.get("/Resources")

            result = search_resources(child_resources)

            if result is not None:
                return result

        return None

    return search_resources(page_obj.get("/Resources"))


@supplementary_information_collector("7.21.4.1-1")
def collect_supplementary_information_7_21_4_1_1(
    veraPdf_violation, pdf, affected_element
) -> list:
    """Extracts the target font object and its used character codes for standard fonts or Form XObjects."""
    page = get_page_from_context(veraPdf_violation, pdf)

    if page is None:
        return []

    base_font_name = extract_first_word(veraPdf_violation.context)

    is_xobject = "/xObject[" in veraPdf_violation.context

    if is_xobject:
        font_obj, xobject = find_font_in_page_xobjects(
            page.obj, base_font_name
        )

        if font_obj is None:
            return []

        used_codes = extract_used_codes_for_xobject_font(
            xobject, font_obj
        )

        return [font_obj, used_codes]

    font_obj = find_font_by_basefont(page.obj, base_font_name)

    if font_obj is None:
        return []

    used_codes = extract_used_codes_for_font_across_pdf(
        pdf, font_obj
    )

    return [font_obj, used_codes]





@supplementary_information_collector("7.21.4.1-2")
def collect_supplementary_information_7_21_4_1_2(
    veraPdf_violation, pdf, affected_element
) -> list:
    """Extracts target font object and all character codes used across the document for rule 7.21.4.1-2."""
    report_debug("im collector")
    report_debug(f"verapdf violation {veraPdf_violation}")

    page = get_page_from_context(veraPdf_violation, pdf)

    base_font_name = extract_first_word(veraPdf_violation.context)

    font_obj = find_font_by_basefont(page.obj, base_font_name)
    if font_obj is None:
        return []

    used_codes = extract_used_codes_for_font_across_pdf(
        pdf, font_obj
    )
    report_debug(f"font obj {font_obj}")
    report_debug(f"used codes , {used_codes}")

    return [font_obj, used_codes]




@supplementary_information_collector("7.21.7-1")
def collect_supplementary_information_7_21_7_1(
    veraPdf_violation, pdf, affected_element
) -> list:
    """Extracts page object, operator index, glyph index, and target font object for rule 7.21.7-1."""
    operator_index, glyph_index = extract_operator_and_glyph_index(
        veraPdf_violation.context
    )
    page = get_page_from_context(veraPdf_violation, pdf)
    base_font_name = extract_first_word(veraPdf_violation.context)
    font_obj = find_font_by_basefont(page.obj, base_font_name)

    return [page, operator_index, glyph_index, font_obj]



# COLLECTOR: 7.21.7-2 and Helper methods


FORBIDDEN = {0x0000, 0xFEFF, 0xFFFE}


def hex_to_int(hex_value):
    """Converts a hex string or bytes sequence into an integer."""
    if isinstance(hex_value, bytes):
        hex_value = hex_value.decode("ascii")

    return int(hex_value, 16)


def parse_to_unicode_violations(cmap_bytes: bytes):
    """Extracts forbidden Unicode mapping violations from raw ToUnicode CMap bytes."""
    violations = []

    lines = cmap_bytes.splitlines()

    mode = None

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if b"beginbfchar" in line:
            mode = "bfchar"
            continue
        elif b"endbfchar" in line:
            mode = None
            continue
        elif b"beginbfrange" in line:
            mode = "bfrange"
            continue
        elif b"endbfrange" in line:
            mode = None
            continue

        if mode == "bfchar":
            match = re.match(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", line
            )
            if not match:
                continue

            src_hex, dst_hex = match.groups()
            dst_int = hex_to_int(dst_hex)

            if dst_int in FORBIDDEN:
                violations.append(
                    {
                        "type": "bfchar",
                        "src": f"<{src_hex.decode()}>",
                        "dst": f"<{dst_hex.decode()}>",
                        "unicode": f"U+{dst_int:04X}",
                    }
                )

        elif mode == "bfrange":
            match_simple = re.match(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>",
                line,
            )

            if match_simple:
                start_hex, end_hex, dst_start_hex = (
                    match_simple.groups()
                )

                start = hex_to_int(start_hex)
                end = hex_to_int(end_hex)
                dst_start = hex_to_int(dst_start_hex)

                length = end - start + 1

                for i in range(length):
                    dst = dst_start + i

                    if dst in FORBIDDEN:
                        violations.append(
                            {
                                "type": "bfrange",
                                "src": f"<{(start + i):X}>",
                                "dst": f"<{dst:04X}>",
                                "unicode": f"U+{dst:04X}",
                            }
                        )
                continue

            match_array = re.match(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*)\]",
                line,
            )

            if match_array:
                start_hex, end_hex, array_content = match_array.groups()
                start = hex_to_int(start_hex)

                entries = re.findall(
                    rb"<([0-9A-Fa-f]+)>", array_content
                )

                for i, dst_hex in enumerate(entries):
                    dst_int = hex_to_int(dst_hex)

                    if dst_int in FORBIDDEN:
                        violations.append(
                            {
                                "type": "bfrange_array",
                                "src": f"<{(start + i):X}>",
                                "dst": f"<{dst_hex.decode()}>",
                                "unicode": f"U+{dst_int:04X}",
                            }
                        )

    return violations


@supplementary_information_collector("7.21.7-2")
def collect_supplementary_information_7_21_7_2(
    veraPdf_violation, pdf, affected_element
) -> list:
    """Extracts invalid Unicode mapping violations from the affected element's ToUnicode CMap stream for rule 7.21.7-2."""
    toUnicode = affected_element

    raw_stream = toUnicode.read_bytes()
    report_debug(f"toUnicode Stream {raw_stream}")
    wrong_Mappings = parse_to_unicode_violations(raw_stream)
    report_debug(f"wrong Mappings {wrong_Mappings}")
    return wrong_Mappings
