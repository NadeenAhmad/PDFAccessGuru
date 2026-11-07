import json
import os
from pikepdf import Array, Dictionary, Name, Pdf
import pikepdf

from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.exceptions.corrector_exceptions.could_not_extract_children_exception import CouldNotExtractChildrenException
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.supplementary_information.supplementary_information import TableStructureContextSupplementaryInformation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_3_robin_hart.utils import normalize_children_of_element
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.tables import CELLS, ROW_GROUPS, CellsWithoutRows, TableRepair

_TABLE_CELL_TAGS = frozenset({Name('/TD'), Name('/TH')})


@corrector("td-not-contained-tr")
def correct_td_not_contained_tr(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.2-9
    Violation description: TD element not contained in TR element

    Correction strategy:
    First, all loose cells of the table part are put into rows at once, by their position on
    the page (cells on the same line form one row) or by the table's column count (see
    structure_repair/tables.py). Only if neither is known, the LLM is asked whether to wrap the
    orphan cell in a new TR or move it into an existing TR.
    """
    if _repair_without_llm(detected_violation.affected_element, pdf):
        return
    supplementary_information: TableStructureContextSupplementaryInformation = detected_violation.supplementary_information[0]  # pyright: ignore[reportAssignmentType]
    parent_of_affected_element = supplementary_information.parent_of_affected_element

    affected_td = _get_affected_table_cell(detected_violation, parent_of_affected_element)
    affected_td_id = find_id_of_affected_element(affected_td, supplementary_information.id_to_table_elements_mapping)
    response = send_prompt(supplementary_information, affected_td_id)

    if response["create_new_tr"] == "true":
        handle_create_new_tr(detected_violation, pdf)
    else:
        handle_existing_tr(response, detected_violation, parent_of_affected_element)


def _repair_without_llm(element, pdf: Pdf) -> bool:
    """True if the loose cells were put into rows (or already are) without the LLM."""
    repair = TableRepair(pdf)
    try:
        if repair.roles.of(element) in CELLS:
            repair.repair_loose_cell(element)
            return repair.roles.is_(element.get("/P"), "TR")
        if repair.roles.of(element) in ("Table",) + ROW_GROUPS:
            repair.repair_group(element)
            return True
    except CellsWithoutRows:
        pass
    return False


def handle_create_new_tr(detected_violation: DetectedViolation, pdf: Pdf):
    """
    Wrap the orphan TD/TH in a new TR element, replacing the cell in its current parent's /K array.
    """
    supplementary_information: TableStructureContextSupplementaryInformation = detected_violation.supplementary_information[0]  # pyright: ignore[reportAssignmentType]
    parent = supplementary_information.parent_of_affected_element
    affected_td = _get_affected_table_cell(detected_violation, parent)

    try:
        parent_children = normalize_children_of_element(parent)
        td_index = next(index for index, child in enumerate(parent_children) if child == affected_td)
    except (CouldNotExtractChildrenException, StopIteration) as e:
        raise CouldNotCorrectDetectedViolationException("td-not-contained-tr") from e

    new_tr = pdf.make_indirect(Dictionary({
        '/Type': Name('/StructElem'),
        '/S': Name('/TR'),
        '/P': parent,
    }))
    new_tr['/K'] = Array([affected_td])
    affected_td['/P'] = new_tr

    if isinstance(parent['/K'], pikepdf.Array):
        parent['/K'][td_index] = new_tr
    else:
        parent['/K'] = new_tr


def handle_existing_tr(response: dict, detected_violation: DetectedViolation, parent_of_affected_element: pikepdf.Object):
    """
    Move the orphan TD/TH from its current parent into an existing TR at the index chosen by the LLM.
    """
    supplementary_information: TableStructureContextSupplementaryInformation = detected_violation.supplementary_information[0]  # pyright: ignore[reportAssignmentType]
    affected_td = _get_affected_table_cell(detected_violation, parent_of_affected_element)
    existing_tr = supplementary_information.id_to_table_elements_mapping[response["id_of_tr_element"]]
    insert_index = response["index_tr_elements_children"]

    try:
        parent_children = normalize_children_of_element(parent_of_affected_element)
        tr_children = normalize_children_of_element(existing_tr)
    except CouldNotExtractChildrenException as e:
        raise CouldNotCorrectDetectedViolationException("td-not-contained-tr") from e

    parent_children = [child for child in parent_children if child != affected_td]
    _set_structure_children(parent_of_affected_element, parent_children)

    tr_children.insert(insert_index, affected_td)
    _set_structure_children(existing_tr, tr_children)
    affected_td['/P'] = existing_tr


def _get_affected_table_cell(
    detected_violation: DetectedViolation,
    parent_of_affected_element: pikepdf.Object,
) -> pikepdf.Object:
    """
    Return the orphan TD/TH to correct.

    Usually this is detected_violation.affected_element. When veraPDF reports a TR
    instead, fall back to the sole direct TD/TH child of the parent.
    """
    affected_element = detected_violation.affected_element
    if affected_element.get('/S') in _TABLE_CELL_TAGS:
        return affected_element

    try:
        orphan_cells = [
            child for child in normalize_children_of_element(parent_of_affected_element)
            if child.get('/S') in _TABLE_CELL_TAGS
        ]
    except CouldNotExtractChildrenException as e:
        raise CouldNotCorrectDetectedViolationException("td-not-contained-tr") from e

    if len(orphan_cells) == 1:
        return orphan_cells[0]

    raise CouldNotCorrectDetectedViolationException("td-not-contained-tr")


def _set_structure_children(element: pikepdf.Object, children: list) -> None:
    if len(children) == 1:
        element['/K'] = children[0]
    elif len(children) > 1:
        element['/K'] = Array(children)
    elif '/K' in element:
        del element['/K']


def send_prompt(supplementary_information: TableStructureContextSupplementaryInformation, affected_td_id: int) -> dict:
    provider = OpenRouterBaseProvider()
    system_prompt, user_prompt = build_prompt_td_not_contained_tr(supplementary_information, affected_td_id)
    response = provider.send_message(system_prompt, user_prompt, json_mode=True)
    response = json.loads(response)
    return response


def build_prompt_td_not_contained_tr(supplementary_information: TableStructureContextSupplementaryInformation, affected_td_id: int) -> tuple[str, str]:
    """
    Builds the system and user prompts for the td-not-contained-tr LLM decision.
    """
    system_prompt = open(os.path.join(os.path.dirname(__file__), 'prompts', 'td_not_containd_tr_system_prompt.txt')).read()

    user_prompt = open(os.path.join(os.path.dirname(__file__), 'prompts', 'td_not_containd_tr_user_prompt.txt')).read()
    user_prompt = user_prompt.replace("{{RENDERED_JSON_DEPICTION_SELECTOR}}", str(supplementary_information.table_json))
    user_prompt = user_prompt.replace("{{ID_BOUNDING_BOX_MAPPING_SELECTOR}}", str(supplementary_information.id_to_bounding_box_mapping_json))
    user_prompt = user_prompt.replace("{{AFFECTED_ELEMENT_ID_SELECTOR}}", str(affected_td_id))

    return (system_prompt, user_prompt)


def find_id_of_affected_element(affected_element: pikepdf.Object, id_to_table_elements_mapping: dict[int, pikepdf.Object]) -> int:
    """
    Finds the id of the affected element in the id_to_table_elements_mapping.
    """
    for id, element in id_to_table_elements_mapping.items():
        if element == affected_element:
            return id
    raise CouldNotCorrectDetectedViolationException("Could not find id of affected element")
