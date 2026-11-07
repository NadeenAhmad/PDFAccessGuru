import pikepdf
from pikepdf import Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


@corrector("non-standard-cmap-embedded")
def correct_non_standard_cmap_embedded(
    detected_violation: DetectedViolation,
    pdf: Pdf
):
    """
    Corrects a non-standard CMap embedded in a Type0 font.

    The corrector reads the CIDSystemInfo from the font's descendant
    CIDFont and uses it to create a custom CMap. This CMap is then
    embedded as the font's new Encoding.
    """

    font = detected_violation.affected_element

    if font.get("/Subtype") != "/Type0":
        return

    cidfont = font["/DescendantFonts"][0]

    cid_info = cidfont["/CIDSystemInfo"]

    registry = cid_info["/Registry"]
    ordering = cid_info["/Ordering"]
    supplement = cid_info["/Supplement"]

    cmap = create_cmap(
        registry,
        ordering,
        supplement
    )

    font["/Encoding"] = pikepdf.Stream(
        pdf,
        cmap
    )


def create_cmap(
    registry,
    ordering,
    supplement
):
    """
    Creates the CMap definition using the given CIDSystemInfo.
    """
    return f"""
/CIDInit /ProcSet findresource begin
12 dict begin
begincmap

/CIDSystemInfo
<<
/Registry ({registry})
/Ordering ({ordering})
/Supplement {supplement}
>>
def

/CMapName /Custom-CMap
/CMapType 1

1 begincodespacerange
<0000> <FFFF>
endcodespacerange

endcmap
CMapName currentdict /CMap defineresource pop
end
end
""".encode("latin1")

