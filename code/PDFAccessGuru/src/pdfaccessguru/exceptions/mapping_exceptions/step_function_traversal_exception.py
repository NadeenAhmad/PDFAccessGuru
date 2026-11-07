
class StepFunctionTraversalException(Exception):
    """
    Raised if the step function is called on a unexpected path segment, index and current pikepdf object.
    This exception is always unexpected and indicates a bug in the step function or the resolve_context function, 
    as it means that there is a path segment in the context of a VeraPDF violation that the 
    step function tries to handle but fails (KeyError, IndexError, AttributeError).
    """
    def __init__(self, segment: str):
        super().__init__(
            f"Map violations step function did run into an unexpected error during traversal of the structured tag tree at segment: {segment}"
        )