


class VeraPdfWrongVersion(Exception):
    """Raised when the version of VeraPDF is not compatible with the expected version."""
    def __init__(self):
        super().__init__("The version of VeraPDF is not compatible with the expected version.")