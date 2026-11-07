


class CouldNotFindAffectedElementException(Exception):
    """
    Raised if the affected element of a VeraPDF violation cannot be found in the PDF document
    and thus resolve_context(...) returns None.
    """
    def __init__(self, message: str = ""):
        super().__init__(message)