

from dataclasses import dataclass

@dataclass
class TaxonomyData:
    """
    Simple data class to represent the relevant data of a Violation from our taxonomy,
    by combining name, description and the guidelines of a Violation (Just the columns of our taxonomy).
    """
    name: str
    description: str
    guidelines: list[str]
    rank: float