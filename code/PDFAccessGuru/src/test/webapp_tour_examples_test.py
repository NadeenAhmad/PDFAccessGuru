"""1.1.3: the guided tour shows what each choice really does, on one example chart."""

from __future__ import annotations

import json
import re

from pdfaccessguru.webapp.pages import TEXT, _tour_examples
from test.webapp_test import _request, app  # noqa: F401  (fixture)


def test_the_examples_are_real_outputs_for_every_choice():
    examples = _tour_examples()
    texts = examples["texts"]
    assert texts["rules"]
    for ai in ("local", "online"):
        assert all(texts[ai][level] for level in ("brief", "standard", "detailed"))
        assert len(texts[ai]["brief"]) < len(texts[ai]["detailed"])          # the levels really differ
    assert examples["contrast"]["ratio_before"] < 4.5 <= examples["contrast"]["ratio_after"]
    assert examples["report"]["summary"] and "The tool wrote" in examples["report"]["review_item"]


def test_the_tour_has_an_example_for_descriptions_colours_and_report(app):  # noqa: F811
    page = _request(app, "GET", f"/{app.token}/?lang=en&tour=1")[2].decode()
    for step in (2, 3, 4):
        assert f'<div class="tour-example" id="tour-ex-{step}" hidden>' in page
    assert len(re.findall(r'<input type="radio" name="tour-ex-ai"', page)) == 3
    assert len(re.findall(r'<input type="radio" name="tour-ex-detail"', page)) == 3
    assert 'src="/' + app.token + '/static/tour-chart.png"' in page and 'alt="Example picture: a bar chart' in page
    data = json.loads(re.search(r"var data = (\{.*?\});\n", page).group(1))
    assert data["texts"]["online"]["detailed"] == _tour_examples()["texts"]["online"]["detailed"]
    status, headers, body = _request(app, "GET", f"/{app.token}/static/tour-chart.png")
    assert status == 200 and headers["Content-Type"] == "image/png" and body.startswith(b"\x89PNG")


def test_the_german_tour_says_the_example_is_an_english_document(app):  # noqa: F811
    page = _request(app, "GET", f"/{app.token}/?lang=de&tour=1")[2].decode()
    assert "Das Beispiel stammt aus einem englischen Dokument" in page and "Wie ausführlich" in page


def test_the_colour_option_says_what_is_wrong_who_it_affects_and_what_changes():
    help_text = TEXT["en"]["contrast_help"]
    assert "light grey on white" in help_text and "low vision" in help_text and "WCAG AA" in help_text
    assert "a little darker" not in help_text
    assert "Sehbehinderung" in TEXT["de"]["contrast_help"]
