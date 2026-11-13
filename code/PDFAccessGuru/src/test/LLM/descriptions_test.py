"""1.1: picture descriptions (level of detail, abbreviations, length), spoken notation and the glyph safeguard."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest

from pdfaccessguru.LLM import descriptions
from pdfaccessguru.LLM.output_checks import plausible_character, spoken_text

FIGURE_FIX = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle."
    "7_3_t01_figure_structure_alternate_description_missing")
GLYPH_FIX = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig."
    "7_21_7_t01_glyph_cannot_mapped_unicode")
INVALID_FIX = importlib.import_module(
    "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_8_babett_ludwig."
    "7_21_7_t02_glyph_invalid_unicode")


@pytest.mark.parametrize("value, expected", [(None, "standard"), ("brief", "brief"), ("DETAILED", "detailed"),
                                             ("long", "standard"), ("", "standard")])
def test_the_level_comes_from_the_setting_and_defaults_to_standard(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("PDFACCESSGURU_DESCRIPTIONS", raising=False)
    else:
        monkeypatch.setenv("PDFACCESSGURU_DESCRIPTIONS", value)
    assert descriptions.level() == expected


def test_each_level_asks_for_its_own_length_and_all_share_the_rules():
    brief, standard, detailed = (descriptions.system_prompt(level) for level in descriptions.LEVELS)
    assert "one short sentence" in brief and "125 characters" in brief
    assert "450 characters" in standard and "180 characters" in standard
    assert "1000 characters" in detailed
    for prompt in (brief, standard, detailed):
        assert "Describe meaning, not looks" in prompt and "never invent what an abbreviation means" in prompt
        assert '{"alt_text"' in prompt
    assert descriptions.length_limit("brief") < descriptions.length_limit("standard") < descriptions.length_limit("detailed")


def test_the_figure_prompt_hands_over_the_documents_abbreviations(monkeypatch):
    monkeypatch.setenv("PDFACCESSGURU_DESCRIPTIONS", "brief")
    system, user = FIGURE_FIX.build_prompt_generate_figure_alt_text('{"page_number":1}',
                                                                  ["EMT: epithelial-mesenchymal transition"])
    assert system == descriptions.system_prompt("brief")
    assert '{"page_number":1}' in user and "- EMT: epithelial-mesenchymal transition" in user
    assert "(none found)" in FIGURE_FIX.build_prompt_generate_figure_alt_text("{}")[1]


def test_abbreviations_are_found_both_ways_and_nothing_is_guessed():
    text = ("Cells undergo epithelial-mesenchymal transition (EMT) in cancer. The World Health Organization (WHO) "
            "says so. Data from the BMI (body mass index) table and messenger RNA (mRNA) levels. With n (n=5), "
            "see (Fig. 3) and the results (OK). The QX (unrelated words here) value.")
    found = dict(line.split(": ", 1) for line in descriptions.abbreviation_definitions(text))
    assert found == {"EMT": "epithelial-mesenchymal transition", "WHO": "World Health Organization",
                     "BMI": "body mass index", "mRNA": "messenger RNA"}


def test_a_too_long_description_keeps_its_whole_first_sentences():
    assert descriptions.shorten("Main finding is X. Second sentence. Third one is long.", 40) == \
        "Main finding is X. Second sentence."
    assert descriptions.shorten("Short.", 40) == "Short."
    cut = descriptions.shorten("word " * 30, 30)
    assert len(cut) <= 30 and cut.endswith("…")


def test_validation_shortens_to_the_chosen_level(monkeypatch):
    monkeypatch.setenv("PDFACCESSGURU_DESCRIPTIONS", "brief")
    text = "Bar chart: sales doubled from 2020 to 2024. " + "Each year adds about a quarter more than before. " * 6
    result = FIGURE_FIX._validate_alt_text(text, SimpleNamespace(violation=SimpleNamespace(name="figure")))
    assert len(result) <= descriptions.length_limit("brief") and result.startswith("Bar chart: sales doubled")


@pytest.mark.parametrize("raw, spoken", [
    ("Quantile q_alpha and q_{0.5}", "Quantile q alpha and q 0.5"),
    ("R^2 = 0.9 and 10^{-3} s", "R² = 0.9 and 10⁻³ s"),
    ("ends with x^2.", "ends with x².") ,
    ("file_name and version 2^3.5 stay", "file_name and version 2^3.5 stay"),
])
def test_notation_is_written_so_a_screen_reader_can_say_it(raw, spoken):
    assert spoken_text(raw) == spoken


@pytest.mark.parametrize("codepoint, allowed", [
    (0x41, True), (0x3B1, True), (0x20D7, True), (0x2192, True), (0x2211, True), (0x2022, True), (0x20AC, True),
    (0x2324, False), (0x03, False), (0xE000, False), (0xFFFD, False), (0x20, False)])
def test_only_plausible_characters_may_come_from_an_ai(codepoint, allowed):
    assert plausible_character(codepoint) is allowed


def test_glyph_names_mupdf_knows_are_used_before_any_ai():
    assert GLYPH_FIX._glyphname_to_unicode_mupdf("/alpha") == "U+03B1"
    assert GLYPH_FIX._glyphname_to_unicode_mupdf("uni20D7") == "U+20D7"
    assert GLYPH_FIX._glyphname_to_unicode_mupdf("g123") is None
    assert GLYPH_FIX._glyphname_to_unicode_mupdf(None) is None


def test_implausible_proposals_for_invalid_mappings_are_dropped():
    assert INVALID_FIX._plausible_mapping("<0041>") and INVALID_FIX._plausible_mapping("<20D7>")
    assert not INVALID_FIX._plausible_mapping("<2324>") and not INVALID_FIX._plausible_mapping("<0020>")
    assert not INVALID_FIX._plausible_mapping("<E000>") and not INVALID_FIX._plausible_mapping("<41>")


def test_the_command_line_offers_exactly_the_three_levels():
    from pdfaccessguru.cli import build_parser

    assert build_parser().parse_args(["fix", "x.pdf", "--descriptions", "detailed"]).descriptions == "detailed"
    assert build_parser().parse_args(["fix", "x.pdf"]).descriptions is None             # the setting decides
    with pytest.raises(SystemExit):
        build_parser().parse_args(["fix", "x.pdf", "--descriptions", "verbose"])


def test_an_ai_request_that_never_finishes_counts_as_failed(monkeypatch):
    import time

    import requests

    from pdfaccessguru.LLM import client

    monkeypatch.setattr(client.requests, "post", lambda url, **kwargs: time.sleep(5))
    started = time.perf_counter()
    with pytest.raises(requests.Timeout):
        client._post_within(0.3, "https://example.invalid")
    assert time.perf_counter() - started < 2
    monkeypatch.setattr(client.requests, "post", lambda url, **kwargs: "answer")
    assert client._post_within(1, "https://example.invalid") == "answer"


def test_the_caption_nearest_to_a_picture_wins_over_the_one_before_it():
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.pictures import _distance
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.structure_repair.layout import Box

    picture = Box(0, 320, 100, 560, 300)                     # right column
    below = Box(0, 320, 305, 560, 330)                       # its caption, right below it
    other_column = Box(0, 40, 700, 280, 730)                 # the caption at the end of the left column
    assert _distance(picture, below) < _distance(picture, other_column)
    assert _distance(picture, None) == float("inf") and _distance(None, below) == float("inf")
    assert _distance(picture, Box(1, 320, 305, 560, 330)) == float("inf")          # another page
