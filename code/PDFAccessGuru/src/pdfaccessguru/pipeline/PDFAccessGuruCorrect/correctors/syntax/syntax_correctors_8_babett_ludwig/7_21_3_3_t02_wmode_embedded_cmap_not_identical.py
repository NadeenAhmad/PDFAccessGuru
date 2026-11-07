from pikepdf import Pdf
from pdfaccessguru.model.detected_violation import DetectedViolation

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


@corrector("wmode-embedded-cmap-not-identical")
def correct_wmode_embedded_cmap_not_identical(
    detected_violation: DetectedViolation,
    pdf: Pdf,
):
    """
    Corrects a mismatch between the WMode value stored in an embedded
    CMap stream and the WMode value of the corresponding CMap dictionary.

    The PDF contains the WMode information in two places. The embedded
    CMap stream contains the actual WMode definition, while the CMap
    dictionary contains a /WMode entry. If these two values are different,
    the PDF contains the corresponding accessibility violation.

    To correct the violation, the function uses the embedded CMap stream
    as the source of truth. The stream is read and decoded so that its
    textual content can be searched for the WMode definition. A regular
    expression extracts the integer value from the `/WMode <value> def`
    definition.

    If no WMode definition can be found in the stream, there is no value
    that can safely be used for the correction, so the function returns
    without making any changes.

    If a WMode value is found, the `/WMode` entry in the CMap dictionary
    is overwritten with the value extracted from the embedded stream.
    This makes both WMode values identical and therefore resolves the
    detected violation.
    """

    cmap = detected_violation.affected_element

    stream = cmap.read_bytes()
    text = stream.decode("latin1")

    # Find the WMode value defined inside the embedded CMap stream.
    import re

    match = re.search(r"/WMode\s+(\d+)\s+def", text)

    if not match:
        return

    embedded_wmode = int(match.group(1))

    # Set the dictionary value to the value defined in the embedded CMap.
    cmap["/WMode"] = embedded_wmode


