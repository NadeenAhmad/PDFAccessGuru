import pikepdf

from pdfaccessguru.utils import describe_pikepdf_element


class CouldNotExtractChildrenException(Exception):
    """
    Raised if children elements of a pikepdf.Object could not be extracted.
    """

    def __init__(self, element: pikepdf.Object):
        super().__init__(f"Could not extract children elements from {describe_pikepdf_element(element)}.")
