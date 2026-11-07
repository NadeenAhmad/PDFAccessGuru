class VeraPdfParseErrorException(Exception):
    """Raised when the veraPDF XML report cannot be parsed."""

    def __init__(self, original_error: Exception | None = None):
        message = "The veraPDF XML report could not be parsed."

        if original_error is not None:
            message = f"{message} Original error: {original_error}"

        super().__init__(message)