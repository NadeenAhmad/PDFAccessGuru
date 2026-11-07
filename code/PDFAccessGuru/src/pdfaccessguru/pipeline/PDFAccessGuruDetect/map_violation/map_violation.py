from pikepdf import Object, Pdf

from pdfaccessguru.model.map_violation.taxonomy_data import TaxonomyData
from pdfaccessguru.model.supplementary_information.supplementary_information import SupplementaryInformation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.collect_supplementary_information.collect_supplementary_information import collect_supplementary_information
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.detect_affected_element import detect_affected_element
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.taxonomy_data_mapping.map_verapdf_violation_to_taxonomy_data import map_verapdf_violation_to_taxonomy_data


def map_verapdf_violation_to_violation(veraPdf_violation: VeraPdfViolation, pdf: Pdf) -> DetectedViolation:
    """
    Maps a {@link VeraPdfViolation} to a {@link DetectedViolation}.

    This mapping includes the following steps:
    - Resolve the context of the VeraPdfViolation to find the affected element in the PDF document.
    - Find and retrieve the needed supplementary information

    Raises: 
        CouldNotFindAffectedElementException: If veraPDFs context could not be resolved to an element in the PDF document.
    """
    affected_element: Object = detect_affected_element(veraPdf_violation, pdf)
    supplementary_information: list[SupplementaryInformation] = collect_supplementary_information(veraPdf_violation, pdf, affected_element)

    taxonomy_data: TaxonomyData = map_verapdf_violation_to_taxonomy_data(veraPdf_violation)

    violation = Violation(
        category = ViolationCategory.SYNTAX,
        name = taxonomy_data.name,
        description=taxonomy_data.description,
        guidelines=taxonomy_data.guidelines,
        rank=taxonomy_data.rank
    )
    detected_violation = DetectedViolation(
        violation = violation,
        affected_element = affected_element,
        supplementary_information=supplementary_information,
        id=generate_detected_violation_id(veraPdf_violation),
        source_context=veraPdf_violation.context,
    )

    return detected_violation

def generate_detected_violation_id(veraPdf_violation: VeraPdfViolation) -> str:
    """
    Defines how the unique identifier of a detected violation is generated.
    A detected violation is uniquely identified by the rule id concatenated with the 
    context of the veraPDF violation.
    """
    return f"{veraPdf_violation.rule_id}-{veraPdf_violation.context}"
