"""
Shared fix for veraPDF rules 5-1 to 5-5 (PDF/UA identification in the XMP metadata).

All five rules are satisfied by one well-formed property: pdfuaid:part = 1, written with
the prefix "pdfuaid" and the PDF/UA namespace. The helper removes every existing PDF/UA
identification property (element or attribute form, any prefix, including amd and corr,
which are optional) and writes a clean one. Other schemas, in particular the PDF/A
identification (pdfaid:part, pdfaid:conformance), are left untouched, and the xpacket
wrapper of the XMP packet is preserved.
"""

from __future__ import annotations

import pikepdf
from lxml import etree

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi.constants import (
    PDFUA_NAMESPACE,
    RDF_NAMESPACE,
)


def metadata_stream(pdf: pikepdf.Pdf, affected_element: object) -> pikepdf.Stream:
    """Return the document's XMP metadata stream (the affected element, or the catalog's /Metadata)."""
    if isinstance(affected_element, pikepdf.Stream):
        return affected_element
    stream = pdf.Root.get("/Metadata")
    if isinstance(stream, pikepdf.Stream):
        return stream
    raise CouldNotCorrectDetectedViolationException("the document has no XMP metadata stream")


def write_pdfua_identification(stream: pikepdf.Stream) -> None:
    """Replace all PDF/UA identification properties with a single pdfuaid:part = 1."""
    try:
        root = etree.fromstring(stream.read_bytes())
    except etree.XMLSyntaxError as error:
        raise CouldNotCorrectDetectedViolationException("the XMP metadata is not well-formed XML") from error

    for element in root.xpath("//*[namespace-uri()=$ns]", ns=PDFUA_NAMESPACE):
        element.getparent().remove(element)
    prefix = f"{{{PDFUA_NAMESPACE}}}"
    for element in root.iter():
        for attribute in [name for name in element.attrib if name.startswith(prefix)]:
            del element.attrib[attribute]
    etree.cleanup_namespaces(root)

    rdf = root if root.tag == f"{{{RDF_NAMESPACE}}}RDF" else root.find(f".//{{{RDF_NAMESPACE}}}RDF")
    if rdf is None:
        raise CouldNotCorrectDetectedViolationException("the XMP metadata has no rdf:RDF element")

    description = etree.SubElement(rdf, f"{{{RDF_NAMESPACE}}}Description", nsmap={"pdfuaid": PDFUA_NAMESPACE})
    description.set(f"{{{RDF_NAMESPACE}}}about", "")
    etree.SubElement(description, f"{{{PDFUA_NAMESPACE}}}part").text = "1"

    # Serialising the tree (not just the root) keeps the <?xpacket ...?> wrapper.
    stream.write(etree.tostring(root.getroottree(), encoding="UTF-8"))
