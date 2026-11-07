


class InvalidPdfPathException(Exception):
    """
    Raised when the provided PDF path is invalid.
    That is if some pdf_path does not point to a file or if the file is not a PDF.
    """
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        super().__init__(f"Invalid PDF path: {pdf_path}. Provided path does not point to a valid PDF file.")