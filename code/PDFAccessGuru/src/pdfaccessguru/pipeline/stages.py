"""
The order in which violations are corrected.

Corrections run in stages. Each stage depends only on the stages before it:

 1. preflight      the file must be readable and editable
 2. fonts          later steps read text, so characters must be right first
 3. structure      everything else attaches to the structure tree
 4. content        what is real content and what is decoration (needs the tree)
 5. semantics      lists, tables, headings, notes (need real content in the tree)
 6. table_headers  header cells can only be linked once rows and cells are right
 7. annotations    links, comments and form fields (need the tree and reading order)
 8. descriptions   pictures and formulas (need final structure and captions)
 9. language       needs correct text; a single element never sets the document language
10. metadata       written once, at the end (title can come from the first heading)

After each stage the file is checked again. A stage is undone if it makes problems of its
own or an earlier stage worse; problems of later stages that appear are "revealed" (some
checks only become possible after earlier repairs) and are handled by those later stages.
This replaces the earlier float "ranks", where almost every rule had rank 100.0 and the
order was decided by the length of the veraPDF context string.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stage:
    name: str
    label: str                      # shown to users while it runs
    rules: frozenset[str]           # veraPDF rule ids ("7.2-34")
    clause_prefixes: tuple[str, ...] = ()   # whole clauses, e.g. "7.21." for all font rules
    # Edits page content: check that pages look the same afterwards.
    touches_content: bool = False
    # May legitimately change the extracted text (e.g. fixing character mappings).
    text_may_change: bool = False
    # Rules whose fix applies to the whole document: only the first occurrence is corrected.
    document_level: frozenset[str] = field(default_factory=frozenset)
    # Rules whose fix applies to a whole page: one correction per page.
    page_level: frozenset[str] = field(default_factory=frozenset)
    # Rules corrected first within the stage (e.g. create the metadata before filling it).
    first: tuple[str, ...] = ()
    # Fixes that create something which veraPDF can then check (an empty metadata block, a
    # structure tree). The problems they reveal are expected and fixed by the next rules, so
    # they are not counted against the fix.
    reveals_by_design: frozenset[str] = field(default_factory=frozenset)
    # Fixes that may change the shape of letters but must keep every character in place
    # (embedding a missing font: viewers showed a look-alike font before).
    shapes_may_change: frozenset[str] = field(default_factory=frozenset)
    # Fixes of a stage that otherwise leaves page content alone but that do edit it (e.g. adding
    # tags to an untagged file): pages must look the same and the text must not change.
    content_rules: frozenset[str] = field(default_factory=frozenset)

    def contains(self, rule_id: str) -> bool:
        return rule_id in self.rules or any(rule_id.startswith(prefix) for prefix in self.clause_prefixes)


def _ids(*ids: str) -> frozenset[str]:
    return frozenset(ids)


def _range(clause: str, first: int, last: int) -> list[str]:
    return [f"{clause}-{number}" for number in range(first, last + 1)]


STAGES: tuple[Stage, ...] = (
    Stage(
        "preflight", "Preparing the file",
        _ids("6.1-1", "7.15-1", "7.16-1", "7.10-1", "7.10-2", "7.11-1", "7.20-1"),
        document_level=_ids("6.1-1", "7.15-1", "7.16-1"),
    ),
    Stage(
        "fonts", "Fixing fonts and characters",
        frozenset(), clause_prefixes=("7.21.",),
        touches_content=True, text_may_change=True,
        # These fixes repair every font of the document at once.
        document_level=_ids("7.21.3.2-1", "7.21.4.1-1", "7.21.5-1", "7.21.6-1", "7.21.6-4", "7.21.8-1"),
        first=("7.21.4.1-1",),                 # embed missing fonts before checking font programs
        shapes_may_change=_ids("7.21.4.1-1"),
    ),
    Stage(
        "structure", "Repairing the structure",
        _ids("7.1-11", "7.1-12", "7.1-4", "7.1-5", "7.1-6", "7.1-7", "6.2-1"),
        document_level=_ids("7.1-11", "7.1-4", "7.1-5", "7.1-6", "6.2-1"),
        first=("7.1-11", "7.1-12"),
        reveals_by_design=_ids("7.1-11"),
        content_rules=_ids("7.1-11"),
    ),
    Stage(
        "content", "Separating content from decoration",
        _ids("7.1-1", "7.1-2", "7.1-3", "7.20-2"),
        touches_content=True,
        content_rules=_ids("7.1-3"),          # only adds marks (or tags the file anew): character-position check
        page_level=_ids("7.1-1", "7.1-2", "7.1-3"),
    ),
    Stage(
        "semantics", "Fixing lists, tables, headings and notes",
        frozenset(_range("7.2", 3, 20) + _range("7.2", 26, 28) + _range("7.2", 36, 43)
                  + ["7.4.2-1", "7.4.4-1", "7.4.4-2", "7.4.4-3", "7.9-1", "7.9-2"]),
        # "the document uses both H and H1-H6": one fix for the whole document
        document_level=_ids("7.4.4-2", "7.4.4-3"),
    ),
    Stage(
        "table_headers", "Linking table headers",
        _ids("7.5-1", "7.5-2"),
    ),
    Stage(
        "annotations", "Fixing links, comments and form fields",
        frozenset(), clause_prefixes=("7.18.",),
        page_level=_ids("7.18.3-1"),
        document_level=_ids("7.18.1-1", "7.18.1-2", "7.18.5-2"),   # done for all annotations at once
    ),
    Stage(
        "descriptions", "Describing pictures and formulas",
        _ids("7.3-1", "7.7-1"),
    ),
    Stage(
        "language", "Setting the language",
        frozenset(["7.2-2"] + _range("7.2", 21, 25) + _range("7.2", 29, 34)),
        document_level=_ids("7.2-2", "7.2-33", "7.2-34"),
    ),
    Stage(
        "metadata", "Fixing the title and file information",
        frozenset(_range("5", 1, 5) + ["7.1-8", "7.1-9", "7.1-10"]),
        document_level=frozenset(_range("5", 1, 5) + ["7.1-8", "7.1-9", "7.1-10"]),
        first=("7.1-8",),
        reveals_by_design=_ids("7.1-8"),
    ),
)


def ordered_rules(stage: Stage, rule_ids) -> list[str]:
    """The stage's rules in correction order: its 'first' rules, then by rule number."""
    def key(rule_id: str):
        priority = stage.first.index(rule_id) if rule_id in stage.first else len(stage.first)
        return (priority, [int(n) for n in re.findall(r"\d+", rule_id)])
    return sorted(rule_ids, key=key)


def stage_of(rule_id: str) -> Stage | None:
    """The stage that corrects this veraPDF rule, or None if no automatic fix exists."""
    for stage in STAGES:
        if stage.contains(rule_id):
            return stage
    return None


def stage_index(rule_id: str) -> int | None:
    stage = stage_of(rule_id)
    return None if stage is None else STAGES.index(stage)


_PAGE = re.compile(r"(?:^|/)pages\[(\d+)\]")


def page_of_context(context: str) -> int | None:
    """0-based page index from a veraPDF context path, if it names one."""
    match = _PAGE.search(context or "")
    return int(match.group(1)) if match else None
