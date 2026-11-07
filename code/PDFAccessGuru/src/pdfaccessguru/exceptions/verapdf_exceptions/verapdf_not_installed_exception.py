class VeraPdfNotInstalledException(Exception):
    """Raised when veraPDF (the accessibility checker) cannot be found."""
    def __init__(self):
        super().__init__(
            "veraPDF (the accessibility checker) is not installed. "
            "Run 'pdfaccessguru doctor --install' to install it."
        )
