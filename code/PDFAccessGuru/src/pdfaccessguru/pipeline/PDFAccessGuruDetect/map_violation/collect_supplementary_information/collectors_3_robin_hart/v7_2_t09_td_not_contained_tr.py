
import io
import itertools
import json

from pdfaccessguru.exceptions.mapping_exceptions.step_function_traversal_exception import StepFunctionTraversalException
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
import pdfplumber
import pikepdf
from pdfplumber.utils.geometry import objects_to_bbox

from pdfaccessguru.model.supplementary_information.supplementary_information import (
    SupplementaryInformation,
    TableStructureContextSupplementaryInformation,
)
from pdfaccessguru.model.supplementary_information.table.bounding_box import BoundingBox
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collect_supplementary_information import supplementary_information_collector
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.resolve_context import resolve_all_elements_on_context, resolve_context_parent_element


_RELEVANT_TABLE_STRUCTURE_TAGS = frozenset({
    pikepdf.Name('/Table'),
    pikepdf.Name('/TD'),
    pikepdf.Name('/TR'),
    pikepdf.Name('/TH'),
    pikepdf.Name('/TFoot'),
    pikepdf.Name('/TBody'),
    pikepdf.Name('/THead'),
})


def _structure_children(element: pikepdf.Object) -> list[pikepdf.Object]:
    if '/K' not in element:
        return []

    children = element['/K']
    if isinstance(children, pikepdf.Array):
        return list(children)
    if isinstance(children, pikepdf.Dictionary):
        return [children]
    return []


def _collect_table_elements(
    element: pikepdf.Object,
    mapping: dict[int, pikepdf.Object],
    next_id: list[int],
) -> None:
    if not isinstance(element, pikepdf.Dictionary):
        return

    tag = element.get('/S')
    if tag not in _RELEVANT_TABLE_STRUCTURE_TAGS:
        return

    mapping[next_id[0]] = element
    next_id[0] += 1

    for child in _structure_children(element):
        _collect_table_elements(child, mapping, next_id)


def resolve_last_table_element(context_path: str, pdf: pikepdf.Pdf) -> pikepdf.Object:
    """
    Resolves the context path and return the last element tagged as /Table in order of context path.

    Args:
        context_path: The context path to resolve.
        pdf: the pikepdf pdf document to resolve the context path in.

    Returns:
        The last element tagged as /Table in order of context path.

    Raises:
        Exception: If no table element is found in the context path.
    """
    elements = resolve_all_elements_on_context(context_path, pdf)
    elements.reverse()
    for element in elements:
        if element is not None and '/S' in element and element.get('/S') == pikepdf.Name('/Table'):
            return element
    raise Exception("Table element not found")


def find_page_number_from_page_element(page_element: pikepdf.Object, pdf: pikepdf.Pdf) -> int:
    """
    Resolve a page dictionary reference to its zero-based index in the PDF.

    Args:
        page_element: Indirect page dictionary from a struct element's /Pg entry.
        pdf: The PDF document to search.

    Returns:
        Zero-based index of the matching page in pdf.pages.

    Raises:
        Exception: When no page in the PDF matches page_element.
    """
    target_objgen = page_element.objgen
    for page_index, page in enumerate(pdf.pages):
        page_obj = page.obj
        if page_obj.objgen != (0, 0) and target_objgen != (0, 0):
            if page_obj.objgen == target_objgen:
                return page_index
        elif page_obj == page_element:
            return page_index
    raise Exception("Could not find page number of page element")  # replace with collector exception


def find_page_number_of_element(element: pikepdf.Object, pdf: pikepdf.Pdf) -> int:
    """
    Find the page number of a given element in a PDF.

    Args:
        element: The StructureTree element to find the page number of.
        pdf: The PDF document to search.

    Returns: 
        The zero-based index of the page in pdf.pages.

    Raises:
        Exception: When the element does not have a /Pg key (reference to a page element)
    """
    page_element = element.get('/Pg')
    if page_element is None:
        raise Exception("Page element not found") # replace with collector exception
    return find_page_number_from_page_element(page_element, pdf)


def generate_id_to_table_elements_mapping(table_element: pikepdf.Object) -> dict[int, pikepdf.Object]:
    """
    Generates a dictionary which maps newly created IDs (starting from 0) to all relevant 
    elements in the subtree of a table element.
    
    Children of the table element are taken into account for the mapping if their tag 
    is /Table, /TD, /TR, /TH, /TFoot, /TBody or /THead.

    Args:
        table_element: The table element to generate the mapping for.
    
    Returns:
        A dictionary which maps newly created IDs (starting from 0) to all relevant
        table structure elements in the subtree.
    """
    mapping: dict[int, pikepdf.Object] = {}
    _collect_table_elements(table_element, mapping, [0])
    return mapping

def _collect_mcids_from_k(k: pikepdf.Object, mcids: list[int]) -> None:
    if isinstance(k, int):
        mcids.append(k)
        return

    if isinstance(k, pikepdf.Dictionary):
        if '/MCID' in k:
            mcids.append(int(k['/MCID']))
        if k.get('/Type') == pikepdf.Name('/MCR'):
            return
        if '/K' in k:
            _collect_mcids_from_k(k['/K'], mcids)
        return

    if isinstance(k, pikepdf.Array):
        for child in k:
            _collect_mcids_from_k(child, mcids)


def find_mcids_of_element(element: pikepdf.Object) -> list[int]:
    """
    Finds MCID values associated with a structure element.

    Collects MCIDs from the element itself (/MCID or integer /K) and from
    marked-content references and nested structure in its /K subtree.
    """
    mcids: list[int] = []
    if not isinstance(element, pikepdf.Dictionary):
        return mcids

    if '/MCID' in element:
        mcids.append(int(element['/MCID']))

    k = element.get('/K')
    if k is None:
        return mcids
    if isinstance(k, int):
        mcids.append(k)
        return mcids

    _collect_mcids_from_k(k, mcids)
    return mcids


def generate_id_to_mcids_mapping(id_to_table_elements_mapping: dict[int, pikepdf.Object]) -> dict[int, list[int]]:
    """
    Generates a dictionary which maps the IDs of table elements that are tagged as /TD or /TH to a list of MCIDs.

    The list of MCIDs is being built by searching for MCID values in the subtree of a table element that is tagged as /TD or /TH.
    """
    mapping: dict[int, list[int]] = {}
    for element_id, element in id_to_table_elements_mapping.items():
        tag = element.get('/S')
        if tag in (pikepdf.Name('/TD'), pikepdf.Name('/TH')):
            mapping[element_id] = find_mcids_of_element(element)
    return mapping


def generate_id_to_bounding_box_mapping(
    id_to_table_elements_mapping: dict[int, pikepdf.Object], 
    page_number: int, 
    pdf_snapshot: io.BytesIO
) -> dict[int, BoundingBox]:
    """
    Generates a dictionary which maps the IDs of table elements that are tagged as /TD or /TH to a bounding box 
    which marks the area that the content of the table element occupies in the pages content stream.

    Args:
        id_to_table_elements_mapping: The mapping of IDs to table elements.
        page_number: The page number of the page that contains the table element.
        pdf_snapshot: The snapshot of the PDF document saved into a in memory buffer.
    Returns:
        A dictionary which maps the IDs of table elements that are tagged as /TD or /TH to a bounding box 
        which marks the area that the content of the table element occupies in the pages content stream.
    """
    id_to_mcids_mapping = generate_id_to_mcids_mapping(id_to_table_elements_mapping)

    result: dict[int, BoundingBox] = {}

    for id, mcids in id_to_mcids_mapping.items():
        bounding_boxes_of_id = []
        for mcid in mcids:
            content_element_bounding_boxes = retrieve_bounding_boxs_of_mcid(mcid, page_number, pdf_snapshot)
            bounding_box_of_mcid = aggregate_bounding_boxes(content_element_bounding_boxes)
            bounding_boxes_of_id.append(bounding_box_of_mcid)
        bounding_box_of_id = aggregate_bounding_boxes(bounding_boxes_of_id)
        result[id] = bounding_box_of_id

    return result

def _plumber_bbox_to_bounding_box(x0: float, top: float, x1: float, bottom: float) -> BoundingBox:
    return BoundingBox(x0=x0, top=top, x1=x1, bottom=bottom)


def retrieve_bounding_boxs_of_mcid(
    mcid: int,
    page_number: int,
    pdf_snapshot: io.BytesIO,
) -> list[BoundingBox]:
    """
    Retrieves the bounding box of a given MCID from the pages content stream.
    Searches for every occurrence of the MCID in the pages content stream and all 
    bounding boxes of the content elements under these occurrences using pdfplumber.
    """
    pdf_snapshot.seek(0)
    bounding_boxes: list[BoundingBox] = []

    with pdfplumber.open(pdf_snapshot) as plumber_pdf:
        page = plumber_pdf.pages[page_number]
        for obj in itertools.chain(page.chars, page.images, page.lines, page.rects, page.curves):
            if obj.get("mcid") != mcid:
                continue
            x0, top, x1, bottom = objects_to_bbox([obj])
            bounding_boxes.append(_plumber_bbox_to_bounding_box(x0, top, x1, bottom))

    return bounding_boxes


def aggregate_bounding_boxes(bounding_boxes: list[BoundingBox]) -> BoundingBox:
    """
    Aggregates a list of bounding boxes into a single bounding box by 
    calculating the smallest bounding box that contains all the bounding boxes in the list.
    """
    if not bounding_boxes:
        raise ValueError("Cannot aggregate an empty list of bounding boxes")

    x0 = min(box.x0 for box in bounding_boxes)
    top = min(box.top for box in bounding_boxes)
    x1 = max(box.x1 for box in bounding_boxes)
    bottom = max(box.bottom for box in bounding_boxes)
    return BoundingBox(x0, top, x1, bottom)


def _is_mapped_table_element(
    element: pikepdf.Object,
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
) -> bool:
    return any(mapped_element == element for mapped_element in id_to_table_elements_mapping.values())


def _find_element_id(
    element: pikepdf.Object,
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
) -> int:
    for element_id, mapped_element in id_to_table_elements_mapping.items():
        if mapped_element == element:
            return element_id
    raise ValueError("Element not found in id_to_table_elements_mapping")


def _table_span_attributes(element: pikepdf.Dictionary) -> dict[str, int]:
    attrs = element.get("/A")
    if attrs is None:
        return {}

    attr_dicts = attrs if isinstance(attrs, pikepdf.Array) else [attrs]
    spans: dict[str, int] = {}
    for attr_dict in attr_dicts:
        if not isinstance(attr_dict, pikepdf.Dictionary):
            continue
        if attr_dict.get("/O") != pikepdf.Name("/Table"):
            continue
        if "/RowSpan" in attr_dict:
            spans["RowSpan"] = int(attr_dict["/RowSpan"])
        if "/ColSpan" in attr_dict:
            spans["ColSpan"] = int(attr_dict["/ColSpan"])
    return spans


def _build_table_json_node(
    element: pikepdf.Object,
    id_to_table_elements_mapping: dict[int, pikepdf.Object],
) -> dict:
    if not isinstance(element, pikepdf.Dictionary):
        raise ValueError("Table structure element must be a dictionary")

    node: dict = {
        "ID": _find_element_id(element, id_to_table_elements_mapping),
        "tag": str(element.get("/S")),
    }
    node.update(_table_span_attributes(element))

    children = []
    for child in _structure_children(element):
        if isinstance(child, pikepdf.Dictionary) and _is_mapped_table_element(
            child, id_to_table_elements_mapping
        ):
            children.append(_build_table_json_node(child, id_to_table_elements_mapping))
    if children:
        node["children"] = children
    return node


def render_table_json(table_element: pikepdf.Object, id_to_table_elements_mapping: dict[int, pikepdf.Object]) -> str:
    """
    Renders a json based representation of the full structure of a table element. Only the relevant children elements
    which are those who have received an ID in the id_to_table_elements_mapping will be included in the json.
    Every node in the json will have the attributes ID, tag and (if available) the RowSpan and ColSpan values of the 
    corresponding table element.
    """
    root_node = _build_table_json_node(table_element, id_to_table_elements_mapping)
    return json.dumps(root_node)

def render_id_to_bounding_box_mapping_json(id_to_bounding_box_mapping: dict[int, BoundingBox]) -> str:
    """
    Renders a JSON representation of the id-to-bounding-box mapping.

    Each bounding box coordinate (x0, top, x1, bottom) is rounded to exactly
    three decimal places before serialization.
    """
    serializable = {
        str(element_id): {
            "x0": round(box.x0, 3),
            "top": round(box.top, 3),
            "x1": round(box.x1, 3),
            "bottom": round(box.bottom, 3),
        }
        for element_id, box in id_to_bounding_box_mapping.items()
    }
    return json.dumps(serializable)

def collect_parent_element(veraPdf_violation: VeraPdfViolation, pdf: pikepdf.Pdf) -> pikepdf.Object:
    """
    Collects the parent element of the affected element.
    """
    try :
        return resolve_context_parent_element(veraPdf_violation.context, pdf)
    except (StepFunctionTraversalException, ValueError) as e:
        raise Exception("Could not find parent element") from e

@supplementary_information_collector("7.2-9")
def collect_supplementary_information_7_2_t09(veraPdf_violation, pdf, affected_element) -> list[SupplementaryInformation]:
    table_element = resolve_last_table_element(veraPdf_violation.context, pdf)
    page_number: int = find_page_number_of_element(table_element, pdf)

    pdf_snapshot = io.BytesIO()
    pdf.save(pdf_snapshot)

    id_to_table_elements_mapping = generate_id_to_table_elements_mapping(table_element)
    id_to_bounding_box_mapping = generate_id_to_bounding_box_mapping(id_to_table_elements_mapping, page_number, pdf_snapshot)

    table_json = render_table_json(table_element, id_to_table_elements_mapping)
    id_to_bounding_box_mapping_json = render_id_to_bounding_box_mapping_json(id_to_bounding_box_mapping)

    parent_of_affected_element = collect_parent_element(veraPdf_violation, pdf)
    
    return [
        TableStructureContextSupplementaryInformation(
            table_json=table_json, 
            id_to_bounding_box_mapping_json=id_to_bounding_box_mapping_json, 
            id_to_table_elements_mapping=id_to_table_elements_mapping, 
            table_element=table_element,
            parent_of_affected_element=parent_of_affected_element
        )
    ]