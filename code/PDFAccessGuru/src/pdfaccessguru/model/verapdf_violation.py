

from dataclasses import dataclass


@dataclass
class VeraPdfViolation :

    """"""
    rule_id: str           # e.g. "7.3-1"
    clause: str            # e.g. "7.3"
    test_number: str       # e.g. "1"
    description: str       # human-readable rule description
    context: str           # veraPDF location path
    message: str           # error message for this specific check

    def __str__(self) -> str:
        return f"[{self.rule_id}] {self.context} - {self.description}"
    
    def get_context(self) -> str:
        """Return the veraPDF location path"""
        return self.context