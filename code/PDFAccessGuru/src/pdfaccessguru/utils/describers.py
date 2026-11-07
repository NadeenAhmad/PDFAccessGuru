"""
Human-readable string descriptions for PDF objects and violation models.
"""

from pikepdf import Dictionary, Object, Pdf

from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.utils.cli_colors import CLIColors


def describe_pikepdf_element(element: Object) -> str:
    """Cheap human-readable summary of a pikepdf object."""
    if element is None:
        return "<none>"
    if isinstance(element, Pdf):
        return f"Pdf ({len(element.pages)} pages)"
    if isinstance(element, Dictionary):
        keys = list(element.keys())
        type_ = element.get("/Type") or element.get("/S") or "Dictionary"
        return f"{type_} keys={keys[:6]}"
    return type(element).__name__


def describe_verapdf_violations(verapdf_violations: list[VeraPdfViolation]) -> str:
    """Human-readable representation of a list of veraPDF violations."""
    count = len(verapdf_violations)
    lines: list[str] = [CLIColors.cyan(f"VeraPDF Violations ({count})")]

    if count == 0:
        lines.append(f"  {CLIColors.green('No violations reported.')}")
        return "\n".join(lines)

    for index, violation in enumerate(verapdf_violations, start=1):
        if index > 1:
            lines.append("")
        lines.extend(_describe_verapdf_violation_lines(violation, index))

    return "\n".join(lines)


def _describe_verapdf_violation_lines(violation: VeraPdfViolation, index: int) -> list[str]:
    return [
        f"  {CLIColors.blue(f'[{index}]')} {CLIColors.cyan(violation.rule_id)}",
        f"    Context:     {violation.context}",
        f"    Description: {violation.description}",
        f"    Message:     {violation.message}",
    ]
