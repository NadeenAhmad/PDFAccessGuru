"""
PDFAccessGuru: finds and fixes accessibility problems in PDF files.

Start the app with `pdfaccessguru`, or use `pdfaccessguru fix file.pdf` on the command line.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pdfaccessguru")
except PackageNotFoundError:  # running from a source checkout without installing
    __version__ = "0.0.0+source"
