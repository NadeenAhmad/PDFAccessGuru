from pikepdf import Dictionary, Pdf

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector


@corrector("display-doc-title-false")
def correct_display_doc_title_false(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.1-10

    Violation: ViewerPreferences dictionary is not present or DisplayDocTitle is set to false.

    Fix: Set ViewerPreferences/DisplayDocTitle = true. If ViewerPreferences does not exist, create it.
    """
    root = pdf.Root

    if '/ViewerPreferences' not in root:
        root['/ViewerPreferences'] = pdf.make_indirect(Dictionary({
            '/DisplayDocTitle': True
        }))
    else:
        root['/ViewerPreferences']['/DisplayDocTitle'] = True
