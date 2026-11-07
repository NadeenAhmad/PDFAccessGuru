from dataclasses import dataclass, field
from typing import Any

from pikepdf import Object

from pdfaccessguru.model.supplementary_information.supplementary_information import SupplementaryInformation
from pdfaccessguru.model.violation import Violation


@dataclass
class DetectedViolation:
    """
    Represents a specific instance of a PDF accessibility violation
    found in a document.

    In particular, every detected violation is associated with a specific violation
    from our taxonomy.
    """

    violation: Violation
    affected_element: Object
    supplementary_information: list[SupplementaryInformation]
    id: str=field(default="")
    source_context: str = field(default="")
