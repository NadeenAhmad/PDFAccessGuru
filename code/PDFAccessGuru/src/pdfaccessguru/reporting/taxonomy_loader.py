from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path


@dataclass(frozen=True)
class TaxonomyEntry:
    category: str
    name: str
    description: str
    guideline: str
    rule: str
    german_explanation: str


def _taxonomy_path() -> Path:
    """The taxonomy table shipped inside the package (works from a checkout and when installed)."""
    return Path(str(files("pdfaccessguru.resources").joinpath("taxonomy.md")))


@lru_cache(maxsize=1)
def load_taxonomy_entries() -> dict[str, TaxonomyEntry]:
    """Load taxonomy rows from the repository-level taxonomy markdown table."""
    path = _taxonomy_path()
    if not path.exists():
        return {}

    entries: dict[str, TaxonomyEntry] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue

        columns = [column.strip() for column in stripped.strip("|").split("|")]
        if len(columns) < 5 or columns[0].lower().replace("*", "") == "category":
            continue

        category = columns[0].strip("* ")
        name = columns[1].strip("` ")
        description = columns[2]
        guideline = columns[3]

        rule = ""
        german_explanation = ""
        if len(columns) >= 6:
            rule = columns[4]
            german_explanation = columns[5]
        else:
            german_explanation = columns[4]

        if name:
            entries[name] = TaxonomyEntry(
                category=category,
                name=name,
                description=description,
                guideline=guideline,
                rule=rule,
                german_explanation=german_explanation,
            )

    return entries


def get_taxonomy_entry(violation_name: str) -> TaxonomyEntry | None:
    return load_taxonomy_entries().get(violation_name)
