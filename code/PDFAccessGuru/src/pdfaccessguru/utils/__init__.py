"""
Utility functions for the PDFAccessGuru project.
This module contains various helper functions that are used across the project.

Helper functions never have side effects, and are pure functions that take input 
and return output without modifying any state!
"""

from pathlib import Path

from pdfaccessguru.exceptions.invalid_pdf_path_exception import InvalidPdfPathException
from pdfaccessguru.utils.describers import (
    describe_pikepdf_element,
    describe_verapdf_violations,
)


def verify_pdf_path(pdf_path: str) :
    """
    Verify that the given pdf_path points to a PDF file.

    That means that the path can be resolved on the users filesystem, 
    that it is a file (not a directory) and that it has the file extension .pdf.

    Raises:
        TypeError: If the given pdf_path is not a string.
        InvalidPdfPathException: If the given pdf_path does not exist, 
            is not a file or does not have the .pdf extension.
    """
    if not isinstance(pdf_path, str):
        raise TypeError("pdf_path must be a string")

    path = Path(pdf_path)
    if not path.exists() or not path.is_file() or path.suffix.lower() != ".pdf":
        raise InvalidPdfPathException(pdf_path)
