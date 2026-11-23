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
    assert len(examples["contrast"]) == 3
    assert all(row["ratio_before"] < 4.5 <= row["ratio_after"] for row in examples["contrast"])
    report = examples["report"]
    assert report["summary"] and "The tool wrote" in report["review_item"]
    assert report["passes"] is True and report["fixed"] > 0 and report["to_review"] > 0     # the same report as numbers
    assert report["review_text"] in report["review_item"] and report["review_page"] == 1


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


def test_the_tour_hides_the_detail_levels_for_simple_rules(app):  # noqa: F811
    page = _request(app, "GET", f"/{app.token}/?lang=en&tour=1")[2].decode()
    assert '$("tour-ex-how").hidden = ai === "rules";' in page


def test_the_examples_show_without_ollama_and_without_an_api_key(app, monkeypatch):  # noqa: F811
    monkeypatch.setattr("pdfaccessguru.LLM.client._ollama_models", lambda url: [])
    monkeypatch.setattr("pdfaccessguru.LLM.client.load_environment_variables", lambda: None)
    for name in ("OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    page = _request(app, "GET", f"/{app.token}/?lang=en&tour=1")[2].decode()
    data = json.loads(re.search(r"var data = (\{.*?\});\n", page).group(1))
    examples = _tour_examples()["texts"]
    assert data["texts"]["local"] == examples["local"] and data["texts"]["online"] == examples["online"]
    assert 'value="local"' in page and 'value="online"' in page          # both AI choices can be tried in the tour


def test_the_colour_example_shows_real_colours_before_and_after(app):  # noqa: F811
    page = _request(app, "GET", f"/{app.token}/?lang=en&tour=1")[2].decode()
    step = page[page.index('id="tour-ex-3"'):page.index('id="tour-ex-4"')]
    for row in _tour_examples()["contrast"]:
        assert f'style="color:{row["before"]}"' in step and f'style="color:{row["after"]}"' in step
    assert "Before: hard to read" in step and "After: easier to read" in step and "Registration closes on 15 March." in step
    assert "#" + "aaaaaa" not in step.replace('style="color:#aaaaaa"', "") and ": 1" not in step   # no colour codes or ratios


def test_the_report_example_is_short_and_visual(app):  # noqa: F811
    page = _request(app, "GET", f"/{app.token}/?lang=en&tour=1")[2].decode()
    step = page[page.index('id="tour-ex-4"'):page.index('class="tour-buttons"')]
    report = _tour_examples()["report"]
    assert '<ul class="tour-ex-tiles">' in step and "passes the automatic check" in step
    assert f'<span class="tour-ex-big">{report["fixed"]}</span> problems fixed' in step
    assert f'<span class="tour-ex-big">{report["to_review"]}</span> texts for you to review' in step
    assert f'src="/{app.token}/static/tour-chart.png" width="120"' in step and "Page 1 · please review" in step
    assert "\u201cBar chart showing the number of participants in the workshop by year. \u2026\u201d" in step
    assert "Staff participation" not in step                                   # only the first sentence
    german = _request(app, "GET", f"/{app.token}/?lang=de&tour=1")[2].decode()
    assert "Probleme behoben" in german and "Vorher: schwer lesbar" in german and "Seite 1 · bitte durchsehen" in german
