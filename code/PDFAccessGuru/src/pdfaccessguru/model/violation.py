from dataclasses import dataclass, field

from pdfaccessguru.model.violation_category import ViolationCategory


@dataclass
class Violation:
    """
    Corresponds to a PDF accessibility violation, as categorized by our taxonomy.
    
    In particular, it does not represent a specific instance of a violation, 
    but rather the general type of violation. Therefore there may exist multiple 
    instances of a Violation in a PDF document, which we represent as DetectedViolation.
    """

    category: ViolationCategory
    name: str
    description: str
    guidelines: list[str]
    rank: float=field(default=0.0)