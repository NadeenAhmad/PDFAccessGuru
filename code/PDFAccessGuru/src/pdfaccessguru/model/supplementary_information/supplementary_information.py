
from dataclasses import dataclass

from pikepdf import Object
import pikepdf

from pdfaccessguru.model.supplementary_information.table.bounding_box import BoundingBox
from pdfaccessguru.model.supplementary_information.table.grid import (
    LogicalTableGrid,
    TableCellCorrectionPlan,
)


class SupplementaryInformation:
    """
    Represents any additional information that may be relevant to a DetectedViolation.

    this is a abstract class, so please create specific subclasses for different types of supplementary information.
    """
    pass


@dataclass
class AnnotationStructureContextSupplementaryInformation(SupplementaryInformation):
    """
    Supplementary structure-tree context for annotation-based repairs.

    Stores where the annotation's OBJR is located in the structure tree and,
    optionally, where the containing structure element itself is nested.
    """

    objr_parent: Object
    objr_index: int | None
    objr_dict: Object
    objr_parent_parent: Object | None = None
    objr_parent_parent_index: int | None = None


@dataclass
class LanguageContextSupplementaryInformation(SupplementaryInformation):
    """
    Language context resolved for generated replacement text.

    source describes where the language came from, for example "page",
    "document", or "default".
    """

    language_tag: str
    source: str


@dataclass
class TableStructureContextSupplementaryInformation(SupplementaryInformation):
    """
    Supplementary information about the structure of a table element in the Structure Tree.

    Used for violation 7.2-9 and 7.2-15 from Robin Hart.
    """
    table_json: str
    id_to_bounding_box_mapping_json: str
    id_to_table_elements_mapping: dict[int, pikepdf.Object]
    table_element: pikepdf.Object
    parent_of_affected_element: pikepdf.Object


@dataclass
class TableCellIntersectionSupplementaryInformation(SupplementaryInformation):
    """
    Supplementary information for table cell intersection violations (7.2-15).

    Contains the logical table grid and the correction plan for the affected cell.
    """

    table_element: pikepdf.Object
    affected_cell_id: int
    id_to_table_elements_mapping: dict[int, pikepdf.Object]
    id_to_parent_tr_mapping: dict[int, pikepdf.Object]
    logical_grid: LogicalTableGrid
    correction_plans: list[TableCellCorrectionPlan]
