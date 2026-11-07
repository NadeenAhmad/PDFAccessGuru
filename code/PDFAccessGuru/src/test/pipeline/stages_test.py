import inspect
import re

from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.taxonomy_data_mapping import (
    map_verapdf_violation_to_taxonomy_data as taxonomy_mapping,
)
from pdfaccessguru.pipeline.stages import STAGES, page_of_context, stage_index, stage_of


def _known_rule_ids() -> list[str]:
    source = inspect.getsource(taxonomy_mapping.map_rule_id_to_syntax_violation_name)
    return re.findall(r'"([0-9.]+-[0-9]+)":', source)


def test_every_known_rule_belongs_to_exactly_one_stage():
    rule_ids = _known_rule_ids()
    assert len(rule_ids) > 90
    for rule_id in rule_ids:
        owners = [stage.name for stage in STAGES if stage.contains(rule_id)]
        assert len(owners) == 1, f"{rule_id} is in {owners}"


def test_dependencies_are_respected_by_the_order():
    def before(a: str, b: str) -> bool:
        return stage_index(a) < stage_index(b)

    assert before("7.21.7-1", "7.2-34")   # characters before language detection
    assert before("7.1-11", "7.1-3")      # structure tree before content classification
    assert before("7.2-9", "7.5-1")       # table rows before table headers
    assert before("7.4.4-2", "7.1-9")     # headings before the title
    assert before("7.18.5-1", "7.3-1")    # links nested before descriptions
    assert stage_index("5-3") == len(STAGES) - 1   # metadata is written last


def test_unknown_rules_have_no_stage():
    assert stage_of("8.2.5.2-1") is None   # a PDF/UA-2 rule without a corrector


def test_page_of_context():
    assert page_of_context("root/document[0]/pages[14](12 0 obj PDPage)/contentStream[0]") == 14
    assert page_of_context("root/document[0]/metadata[0]") is None
