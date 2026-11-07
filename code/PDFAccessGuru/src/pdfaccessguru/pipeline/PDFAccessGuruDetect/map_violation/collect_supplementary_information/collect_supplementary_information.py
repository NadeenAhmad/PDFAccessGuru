
from collections.abc import Callable
from typing import Dict

from pikepdf import Object, Pdf

from pdfaccessguru.model.supplementary_information.supplementary_information import SupplementaryInformation
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation


_SUPPLEMENTARY_INFORMATION_COLLECTOR_FUNCTIONS: Dict[str, Callable[[VeraPdfViolation, Pdf, Object], list[SupplementaryInformation]]] = {}


def collect_supplementary_information(veraPdf_violation: VeraPdfViolation, pdf: Pdf, affected_element: Object) -> list[SupplementaryInformation]:
    """
    """
    rule_id = veraPdf_violation.rule_id
    collector_function = _SUPPLEMENTARY_INFORMATION_COLLECTOR_FUNCTIONS.get(rule_id, default_supplementary_information_collector)
    return collector_function(veraPdf_violation, pdf, affected_element)

def default_supplementary_information_collector(veraPdf_violation: VeraPdfViolation, pdf: Pdf, affected_element: Object) -> list[SupplementaryInformation] :
    """
    If no specific collector was specified the supplementary_information should be an empty list.
    """
    return  []

def supplementary_information_collector(rule_id: str):
    """
    Decorator to register an supplementary information collector 
    function for a specific rule_id of a {@link VeraPdfViolation}.

    Parameters:
        - rule_id: the key for the dictionary of all supplementary_information_collector's.
        Must be the rule_id parameter of some {@link VeraPdfViolation}
    """
    def decorator(func: Callable[[VeraPdfViolation, Pdf, Object], list[SupplementaryInformation]]):
        _SUPPLEMENTARY_INFORMATION_COLLECTOR_FUNCTIONS[rule_id] = func
        return func
    return decorator


# Import registry for collector-registration side effects after the decorator exists.
import pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.registry  # noqa: E402,F401
import pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collectors_3_robin_hart.v7_2_t09_td_not_contained_tr # noqa: E402,F401
import pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collectors_3_robin_hart.v7_2_t15_table_cell_intersection_other_cells # noqa: E402,F401
