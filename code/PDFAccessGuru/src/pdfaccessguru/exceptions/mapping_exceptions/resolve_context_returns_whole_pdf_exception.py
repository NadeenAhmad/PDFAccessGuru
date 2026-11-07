

from pdfaccessguru.exceptions.mapping_exceptions.could_not_find_affected_element_exception import CouldNotFindAffectedElementException
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation


class ResolveContextReturnsWholePdfException(CouldNotFindAffectedElementException) :
    """
    Raised if the function resolve_context does return the whole pikepdf.Pdf object, which 
    is not of type pikepdf.Object. If raised the {@link Violation} cannot use 
    default_affected_element_finder and therefore a designated affected_element_finder
    has to be implemented.
    """
    def __init__(self, veraPdf_violation: VeraPdfViolation):
        print("Function resolve_context did return whole pikepdf.Pdf object. " \
            f"Please implement a designated affected_element_finder for veraPdf violation '{veraPdf_violation.rule_id}'")
        super().__init__()