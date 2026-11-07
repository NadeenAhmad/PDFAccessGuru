"""Unit tests for `_detect_syntax_violations` sort order and the empty-input path.

These tests do **not** run veraPDF or the real mapper. `_stub_syntax_detection`
replaces `run_verapdf` and `map_verapdf_violation_to_violation` on the `detect`
module (the names `detect.py` actually calls) so the function under test only
maps a canned list of `DetectedViolation` objects through `SortedKeyList`.

Production sort key: `(violation.rank, len(id), id)` — lower rank first, then
shorter id, then lexicographic id. The four sort tests check each key in
isolation and then all three together. The fifth test checks that an empty
veraPDF result yields `[]`.

They work correctly for that scope: monkeypatches hit the right module
namespace; reporting is a no-op without a pipeline report session; all five
assertions match `SortedKeyList` tuple comparison. They do not cover the public
`detect()` wrapper, mapping/veraPDF themselves, or the exception paths that
skip a violation (`CouldNotFindAffectedElementException` / generic `Exception`).
"""

from unittest.mock import MagicMock

import pytest

from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.model.verapdf_violation import VeraPdfViolation
from pdfaccessguru.model.violation import Violation
from pdfaccessguru.model.violation_category import ViolationCategory
from pdfaccessguru.pipeline.PDFAccessGuruDetect import detect as detect_module


def _make_verapdf_violation(index: int) -> VeraPdfViolation:
    return VeraPdfViolation(
        rule_id=f"7.0-{index}",
        clause="7.0",
        test_number=str(index),
        description="",
        context=f"context[{index}]",
        message="",
    )


def _make_detected_violation(*, rank: float, violation_id: str) -> DetectedViolation:
    return DetectedViolation(
        violation=Violation(
            category=ViolationCategory.SYNTAX,
            name="stub-violation",
            description="",
            guidelines=[],
            rank=rank,
        ),
        affected_element=MagicMock(),
        supplementary_information=[],
        id=violation_id,
    )


def _stub_syntax_detection(
    monkeypatch: pytest.MonkeyPatch,
    detected_violations: list[DetectedViolation],
) -> None:
    """Stub veraPDF and mapping so tests only exercise sorting of DetectedViolation objects."""
    verapdf_violations = [_make_verapdf_violation(i) for i in range(len(detected_violations))]
    mapping = {
        verapdf_violation.rule_id: detected_violation
        for verapdf_violation, detected_violation in zip(
            verapdf_violations, detected_violations
        )
    }

    monkeypatch.setattr(detect_module, "run_verapdf", lambda _pdf_path, _cancel_event=None: verapdf_violations)

    def _map_verapdf_violation_to_violation(verapdf_violation, _pdf):
        return mapping[verapdf_violation.rule_id]

    monkeypatch.setattr(
        detect_module,
        "map_verapdf_violation_to_violation",
        _map_verapdf_violation_to_violation,
    )


def _detect() -> list[DetectedViolation]:
    return detect_module._detect_syntax_violations("unused.pdf", MagicMock())


def test_detect_syntax_violations_sorts_by_rank_ascending(monkeypatch: pytest.MonkeyPatch):
    unsorted = [
        _make_detected_violation(rank=5.0, violation_id="id-a"),
        _make_detected_violation(rank=1.0, violation_id="id-b"),
        _make_detected_violation(rank=3.0, violation_id="id-c"),
    ]
    _stub_syntax_detection(monkeypatch, unsorted)

    result = _detect()

    assert [detected.violation.rank for detected in result] == [1.0, 3.0, 5.0]
    assert [detected.id for detected in result] == ["id-b", "id-c", "id-a"]


def test_detect_syntax_violations_sorts_by_id_length_when_ranks_equal(
    monkeypatch: pytest.MonkeyPatch,
):
    unsorted = [
        _make_detected_violation(rank=1.0, violation_id="ccc"),
        _make_detected_violation(rank=1.0, violation_id="a"),
        _make_detected_violation(rank=1.0, violation_id="bb"),
    ]
    _stub_syntax_detection(monkeypatch, unsorted)

    result = _detect()

    assert [detected.id for detected in result] == ["a", "bb", "ccc"]


def test_detect_syntax_violations_sorts_by_id_lexicographically_when_rank_and_length_equal(
    monkeypatch: pytest.MonkeyPatch,
):
    unsorted = [
        _make_detected_violation(rank=1.0, violation_id="c-id"),
        _make_detected_violation(rank=1.0, violation_id="a-id"),
        _make_detected_violation(rank=1.0, violation_id="b-id"),
    ]
    _stub_syntax_detection(monkeypatch, unsorted)

    result = _detect()

    assert [detected.id for detected in result] == ["a-id", "b-id", "c-id"]


def test_detect_syntax_violations_applies_full_sort_key_rank_then_id_length_then_id(
    monkeypatch: pytest.MonkeyPatch,
):
    unsorted = [
        _make_detected_violation(rank=2.0, violation_id="z"),
        _make_detected_violation(rank=1.0, violation_id="bbb"),
        _make_detected_violation(rank=1.0, violation_id="ab"),
        _make_detected_violation(rank=1.0, violation_id="aa"),
    ]
    _stub_syntax_detection(monkeypatch, unsorted)

    result = _detect()

    assert [(detected.violation.rank, detected.id) for detected in result] == [
        (1.0, "aa"),
        (1.0, "ab"),
        (1.0, "bbb"),
        (2.0, "z"),
    ]


def test_detect_syntax_violations_returns_empty_list_when_verapdf_finds_nothing(
    monkeypatch: pytest.MonkeyPatch,
):
    _stub_syntax_detection(monkeypatch, [])

    result = _detect()

    assert result == []
