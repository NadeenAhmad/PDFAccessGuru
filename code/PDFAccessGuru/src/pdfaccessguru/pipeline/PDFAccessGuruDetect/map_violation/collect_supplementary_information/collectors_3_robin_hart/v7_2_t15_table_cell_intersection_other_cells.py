import pikepdf
from pikepdf import Dictionary, Name, Object, Pdf

from pdfaccessguru.model.supplementary_information.supplementary_information import (
    SupplementaryInformation,
    TableCellIntersectionSupplementaryInformation,
)
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collect_supplementary_information import (
    supplementary_information_collector,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collectors_3_robin_hart.table_grid_analysis import (
    analyze_table_grid,
    find_ancestor_table,
    find_element_id,
    generate_id_to_table_elements_mapping,
)

_TABLE_CELL_TAGS = frozenset({Name("/TD"), Name("/TH")})


@supplementary_information_collector("7.2-15")
def collect_supplementary_information_7_2_t15(
    veraPdf_violation: VeraPdfViolation,
    pdf: Pdf,
    affected_element: Object,
) -> list[SupplementaryInformation]:
    if not isinstance(affected_element, pikepdf.Dictionary):
        raise ValueError("Affected element must be a structure dictionary")
    if affected_element.get("/S") not in _TABLE_CELL_TAGS:
        raise ValueError("Affected element must be a /TD or /TH table cell")

    table_element = find_ancestor_table(affected_element)
    id_to_table_elements_mapping = generate_id_to_table_elements_mapping(table_element)
    affected_cell_id = find_element_id(affected_element, id_to_table_elements_mapping)
    analysis = analyze_table_grid(
        table_element,
        id_to_table_elements_mapping,
        affected_cell_id,
    )

    return [
        TableCellIntersectionSupplementaryInformation(
            table_element=table_element,
            affected_cell_id=affected_cell_id,
            id_to_table_elements_mapping=id_to_table_elements_mapping,
            id_to_parent_tr_mapping=analysis.id_to_parent_tr_mapping,
            logical_grid=analysis.logical_grid,
            correction_plans=analysis.correction_plans,
        )
    ]
