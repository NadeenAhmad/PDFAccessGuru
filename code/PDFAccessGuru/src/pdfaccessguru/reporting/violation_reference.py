from __future__ import annotations

import re

from pdfaccessguru.reporting.taxonomy_loader import load_taxonomy_entries


VIOLATION_REFERENCE_FILENAME = "violation_reference.md"


def build_violation_reference_markdown() -> str:
    """Build the customer-facing reference for every syntax violation."""
    syntax_entries = [
        entry
        for entry in load_taxonomy_entries().values()
        if entry.category.casefold() == "syntax"
    ]

    lines = [
        "# Violation Reference",
        "",
        "This reference lists the syntax accessibility violations checked by PDFAccessGuru.",
        "",
        "| Violation | Rule | Guideline | Description | Explanation |",
        "|---|---|---|---|---|",
    ]

    for entry in syntax_entries:
        anchor = violation_reference_anchor(entry.name)
        lines.append(
            "| "
            f'<a id="{anchor}"></a>`{_escape_table(entry.name)}` | '
            f"{_escape_table(entry.rule)} | "
            f"{_escape_table(entry.guideline)} | "
            f"{_escape_table(entry.description)} | "
            f"{_escape_table(entry.german_explanation)} |"
        )

    lines.append("")
    return "\n".join(lines)


def violation_reference_anchor(violation_name: str) -> str:
    """Return the stable fragment identifier used by report links."""
    normalized_name = re.sub(r"[^a-z0-9]+", "-", violation_name.casefold()).strip("-")
    return f"violation-{normalized_name}"


def violation_reference_link(violation_name: str) -> str:
    """Return a relative Markdown link to one violation's reference row."""
    anchor = violation_reference_anchor(violation_name)
    return f"[{violation_name}]({VIOLATION_REFERENCE_FILENAME}#{anchor})"


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
