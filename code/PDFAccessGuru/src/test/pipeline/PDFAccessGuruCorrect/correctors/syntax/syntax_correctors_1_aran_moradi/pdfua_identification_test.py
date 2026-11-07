import pikepdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_1_aran_moradi.pdfua_identification import (
    write_pdfua_identification,
)

XMP_WITH_PDFA_AND_BROKEN_PDFUA = b"""<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about="" xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/"
      pdfaid:part="2" pdfaid:conformance="A"/>
  <rdf:Description rdf:about="" xmlns:ns0="http://www.aiim.org/pdfua/ns/id/">
   <ns0:part>2</ns0:part>
   <ns0:amd>broken</ns0:amd>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>"""


def test_pdfua_identification_is_rewritten_and_pdfa_identification_is_kept():
    pdf = pikepdf.new()
    stream = pdf.make_stream(XMP_WITH_PDFA_AND_BROKEN_PDFUA)

    write_pdfua_identification(stream)

    xmp = stream.read_bytes()
    assert b'pdfaid:part="2"' in xmp
    assert b'pdfaid:conformance="A"' in xmp
    assert b"<pdfuaid:part>1</pdfuaid:part>" in xmp
    assert b"ns0:" not in xmp
    assert b"amd" not in xmp
    assert xmp.startswith(b"<?xpacket begin=")
    assert xmp.rstrip().endswith(b'<?xpacket end="w"?>')
