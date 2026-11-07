
class CouldNotCorrectDetectedViolationException(Exception):
    """
    Raised if some corrector was (for some expected reason) 
    not able to correct the given {@link DetectedViolation}.
    """
    def __init__(self, message: str = ""):
        super().__init__(message)