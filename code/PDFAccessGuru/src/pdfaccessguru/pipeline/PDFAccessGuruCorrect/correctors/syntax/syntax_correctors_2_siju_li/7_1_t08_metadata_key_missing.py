from pikepdf import Name, Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


@corrector("metadata-key-missing")
def correct_metadata_key_missing(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.1-8

    Violation: /Metadata entry is missing from the document catalog, or the metadata
    stream dictionary does not contain Type=/Metadata or Subtype=/XML.

    Fix: Add a minimal valid XMP metadata stream to the document catalog.
    """
    root = pdf.Root

    if '/Metadata' not in root:
        minimal_xmp = (
            b'<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>'
            b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            b'<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            b'</rdf:RDF>'
            b'</x:xmpmeta>'
            b'<?xpacket end="w"?>'
        )
        metadata_stream = pdf.make_stream(minimal_xmp)
        metadata_stream['/Type'] = Name('/Metadata')
        metadata_stream['/Subtype'] = Name('/XML')
        root['/Metadata'] = pdf.make_indirect(metadata_stream)
    else:
        metadata = root['/Metadata']
        if '/Type' not in metadata:
            metadata['/Type'] = Name('/Metadata')
        if '/Subtype' not in metadata:
            metadata['/Subtype'] = Name('/XML')
