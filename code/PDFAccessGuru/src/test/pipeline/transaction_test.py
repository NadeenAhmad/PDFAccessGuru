from dataclasses import dataclass

from pdfaccessguru.pipeline.stages import stage_of
from pdfaccessguru.pipeline.transaction import judge_fix


@dataclass
class _Finding:
    rule_id: str


def _judge(rule: str, before: dict, after: dict):
    to_list = lambda counts: [_Finding(r) for r, n in counts.items() for _ in range(n)]
    return judge_fix(rule, stage_of(rule), to_list(before), to_list(after), b"", "unused.pdf")


def test_language_fix_that_reveals_other_problems_is_kept():
    # Measured on energies-16-03661-v4.pdf: setting the document language removes 4,243
    # findings and lets veraPDF check content and links it skipped before.
    verdict = _judge("7.2-34", {"7.2-34": 4243, "7.1-3": 4339, "7.18.5-1": 459},
                     {"7.2-34": 0, "7.1-3": 4428, "7.18.5-1": 503})
    assert verdict.keep and verdict.fixed == 4243 and verdict.revealed == 133


def test_fix_that_fixes_nothing_but_breaks_something_is_undone():
    verdict = _judge("7.5-1", {"7.5-1": 1}, {"7.5-1": 1, "6.2-1": 1})
    assert not verdict.keep and "fixed nothing" in verdict.reason


def test_fix_that_breaks_more_than_it_fixes_is_undone():
    verdict = _judge("7.2-43", {"7.2-43": 1}, {"7.5-1": 2})
    assert not verdict.keep and "more new problems" in verdict.reason


def test_fix_that_makes_its_own_rule_worse_is_undone():
    verdict = _judge("7.2-17", {"7.2-17": 1}, {"7.2-17": 3})
    assert not verdict.keep and "same kind" in verdict.reason


def test_equal_trade_is_kept_and_reported():
    verdict = _judge("7.2-43", {"7.2-43": 1, "7.5-1": 37}, {"7.5-1": 38})
    assert verdict.keep and verdict.fixed == 1 and verdict.revealed == 1


def test_fix_is_judged_by_all_problems_that_disappear():
    # Setting the language for rule 7.2-2 also removes the 7.2-34 findings at once.
    verdict = _judge("7.2-2", {"7.2-2": 1, "7.2-34": 4313, "7.1-3": 4339},
                     {"7.2-34": 0, "7.1-3": 4443})
    assert verdict.keep and verdict.fixed == 4314 and verdict.revealed == 104


def test_creating_the_metadata_block_is_kept_although_it_reveals_problems():
    # An empty metadata block lets veraPDF check the title and the PDF/UA identification;
    # the next rules of the metadata stage fill them in.
    verdict = _judge("7.1-8", {"7.1-8": 1}, {"5-1": 1, "7.1-9": 1})
    assert verdict.keep
