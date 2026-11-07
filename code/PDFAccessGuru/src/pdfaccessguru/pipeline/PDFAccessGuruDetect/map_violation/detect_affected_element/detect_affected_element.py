from collections.abc import Callable
from typing import Dict

from pikepdf import Object, Pdf

from pdfaccessguru.exceptions.mapping_exceptions.could_not_find_affected_element_exception import CouldNotFindAffectedElementException
from pdfaccessguru.exceptions.mapping_exceptions.resolve_context_returns_whole_pdf_exception import ResolveContextReturnsWholePdfException
from pdfaccessguru.exceptions.mapping_exceptions.step_function_traversal_exception import StepFunctionTraversalException
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.resolve_context import _resolve_context
from pdfaccessguru.pipeline.reporting import report_error


_AFFECTED_ELEMENT_DETECTOR_FUNCTIONS: Dict[str, Callable[[VeraPdfViolation, Pdf], Object]] = {}




def detect_affected_element(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    """
    Detect the affected element in the structured pdf tree provided by pikepdf.

    By default the detection of the affected element relies on the function resolve_context,
    which uses to step() function to traverse the while context path of the veraPdf_violation.
    Optionally (if the resolve_context function and therefore just traversing the 
    step function is not enough for the Violation), 
    own affected_element_detector's can be defined for a Syntax Violation.
    The implementation of each of those affected_element_detector's can be found inside 
    file {@link registry}. 
    During runtime the affected_element_detector's (which are essentially functions) are stored 
    inside _AFFECTED_ELEMENT_DETECTOR_FUNCTIONS. The key is the rule_id of the veraPdf_violation.

    Raises: 
    - exception {@link CouldNotFindAffectedElementException} if 
        the affected element cannot be found in the PDF document.
    """
    rule_id = veraPdf_violation.rule_id
    detector_function = _AFFECTED_ELEMENT_DETECTOR_FUNCTIONS.get(rule_id, default_affected_element_detector)
    return detector_function(veraPdf_violation, pdf)


def default_affected_element_detector(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> Object:
    """
    Default detector function for affected element. It resolves the whole 
    context of the {@link VeraPdfViolation} by traversing the step function.

    Raises:
        - CouldNotFindAffectedElementException: if the affected element cannot 
        be found in the PDF document.
        - ResolveContextReturnsWholePdfException: if _resolve_context provides 
        the whole pdf as affected element. See definition ResolveContextReturnsWholePdfException.
    """
    context: str = veraPdf_violation.context
    try:
        affected_element = _resolve_context(context, pdf)
    except StepFunctionTraversalException as e:
        report_error(f"There was an step function traversal exception: {str(e)}")
        raise CouldNotFindAffectedElementException() from e
    if isinstance(affected_element, Pdf) :
        raise ResolveContextReturnsWholePdfException(veraPdf_violation)

    return affected_element


def affected_element_detector(rule_id: str):
    """
    Decorator to register an affected element detector 
    function for a specific rule_id of a {@link VeraPdfViolation}.

    Parameters:
        - rule_id: the key for the dictionary of all affected_element_detector's.
        Must be the rule_id parameter of some {@link VeraPdfViolation}
    """
    def decorator(func: Callable[[VeraPdfViolation, Pdf], Object]):
        _AFFECTED_ELEMENT_DETECTOR_FUNCTIONS[rule_id] = func
        return func
    return decorator


# Import registry after the decorator exists so decorated detector functions are
# registered during normal pipeline execution.
import pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.registry  # noqa: E402,F401

