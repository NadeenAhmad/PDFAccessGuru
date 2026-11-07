from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pikepdf import Name, Pdf
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import CouldNotCorrectDetectedViolationException


# Highest version PDF/UA-1 permits: the header must read "%PDF-1.n" with n in 0..7.
PDFUA_MAX_VERSION = "1.7"

# Name of the attribute this corrector sets on the Pdf object. A save site that
# wants the header to be rewritten has to read it and pass it to Pdf.save as
# force_version, because the header is only written when the file is saved.
FORCED_VERSION_ATTRIBUTE = "forced_pdf_version"


@corrector("invalid-pdf-version")
def correct_invalid_pdf_version(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 6.1-1
    Violation description: The file header shall consist of "%PDF-1.n" followed by
    a single EOL marker, where 'n' is a single digit number between 0 and 7.
    A file written as PDF 2.0 therefore starts with "%PDF-2.0" and is reported.
    Correction strategy:
    The version is lowered to the highest version PDF/UA-1 allows, 1.7. Two things
    carry a PDF version, and both are set:
    - the document catalog's /Version entry, which is the version a reader honours
      over the header, is set to /1.7 so the catalog does not keep declaring a
      version the header is not allowed to have.
    - the required header version is recorded on the Pdf object as the attribute
      named by FORCED_VERSION_ATTRIBUTE.
    Before correction:
    %PDF-2.0
    ...|
       |_/Catalog (no /Version, or /Version 2.0)
    After correction:
    %PDF-1.7
    ...|
       |_/Catalog|
                  |_/Version /1.7

    Known limitation:
    The file header is not part of the object model: pikepdf exposes Pdf.pdf_version
    read-only and only writes a header when the document is saved, so the header can
    only be changed by passing force_version to Pdf.save. A corrector receives the
    already opened Pdf and never saves it itself, which means it cannot rewrite the
    header on its own. Setting the catalog's /Version alone does not satisfy the
    rule either, because veraPDF checks the header bytes (verified: saving with
    /Version set but without force_version still produces "%PDF-2.0").
    This corrector therefore records the required version on the Pdf object, and a
    save site clears the rule by honouring it:
        forced_version = getattr(pdf, FORCED_VERSION_ATTRIBUTE, None)
        pdf.save(output_path, force_version=forced_version) if forced_version \
            else pdf.save(output_path)
    The save sites in the pipeline and in the test helpers do not read the attribute
    yet, so rule 6.1-1 is not cleared end-to-end until they do. Wiring them up was
    deliberately left out of this corrector because it changes shared code.
    """

    try:
        pdf.Root["/Version"] = Name(f"/{PDFUA_MAX_VERSION}")
        setattr(pdf, FORCED_VERSION_ATTRIBUTE, PDFUA_MAX_VERSION)
    except Exception as e:
        raise CouldNotCorrectDetectedViolationException("invalid-pdf-version") from e
