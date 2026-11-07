import pikepdf
from pikepdf import Pdf
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException


@corrector("dynamic-xfa-forms-present")
def correct_dynamic_xfa_forms_present(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.15-1

    Violation description:
    Dynamic XFA forms are present in the PDF document.

    Correction strategy:
    Remove the /XFA key from the /AcroForm dictionary to conform to PDF/UA standards.
    """
    affected_element = detected_violation.affected_element

    # XFA data can be a pikepdf.Stream or pikepdf.Array, so we check for generic pikepdf.Object
    if not isinstance(affected_element, pikepdf.Object):
        raise CouldNotCorrectDetectedViolationException("dynamic-xfa-forms-present")
    
    # Correct way to delete entries from the actual PDF document catalog structure
    if "/AcroForm" in pdf.Root and "/XFA" in pdf.Root["/AcroForm"]:
        del pdf.Root["/AcroForm"]["/XFA"]
    else:
        raise CouldNotCorrectDetectedViolationException("dynamic-xfa-forms-present")