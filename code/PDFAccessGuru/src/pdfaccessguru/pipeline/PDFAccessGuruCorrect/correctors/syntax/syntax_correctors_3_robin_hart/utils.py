import pikepdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_extract_children_exception import CouldNotExtractChildrenException


def normalize_children_of_element(element: pikepdf.Object) -> list:
    """
    Helper to safely extract children elements of a pikepdf.Object as a Python list.
    pikepdf.Object can store children elements either inside a pikepdf.Dictionary or a pikepdf.Array.

    Args:
        element: pikepdf.Object, contains children elements either as a pikepdf.Dictionary or a pikepdf.Array

    Returns:
        list: list of children elements, maybe empty if element does not contain children elements

    Raises:
        CouldNotExtractChildrenException: If children elements of the given element could not be extracted.
    """
    if '/K' not in element:
        return []

    children = element['/K']
    if isinstance(children, pikepdf.Dictionary):
        return [children]
    if isinstance(children, pikepdf.Array):
        return list(children)
    if isinstance(children, int):
        return [children]
        
    raise CouldNotExtractChildrenException(element)
