"""Phase 12b: the start page says what stays on the computer, and every option explains itself in its box."""

from __future__ import annotations

import os
import re

import pytest

from pdfaccessguru.webapp import server as server_module
from pdfaccessguru.webapp.server import App, Job
from test.webapp_test import _request, app  # noqa: F401  (fixture)

SECRET = "sk-" + "proj-" + "NOT-A-REAL-KEY-0123456789"   # built in pieces, so key scans do not flag this file


def _start_page(app, monkeypatch, model="", openai_key="", language="en"):  # noqa: F811
    monkeypatch.setattr("pdfaccessguru.LLM.client._ollama_models", lambda url: [model] if model else [])
    monkeypatch.setattr("pdfaccessguru.LLM.client.load_environment_variables", lambda: None)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    if openai_key:
        monkeypatch.setenv("OPENAI_API_KEY", openai_key)
    else:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    return _request(app, "GET", f"/{app.token}/?lang={language}")[2].decode()


def _radio(page: str, value: str) -> str:
    return re.search(rf'<input type="radio" id="ai-{value}"[^>]*>', page).group(0)


def test_without_ollama_and_key_simple_rules_are_chosen_and_the_others_say_what_is_missing(app, monkeypatch):  # noqa: F811
    page = _start_page(app, monkeypatch)
    assert "checked" in _radio(page, "none")
    assert "disabled" in _radio(page, "ollama") and "disabled" in _radio(page, "cloud")
    assert "Not installed or not running" in page and "No key set up yet" in page
    import os
    from pathlib import Path
    if os.name != "nt":
        assert str(Path.home()) not in page and "~/" in page          # no user name in screenshots
    assert "Stays on your computer (recommended for confidential files)" in page
    assert "Sent over the internet" in page


def test_with_ollama_the_ai_on_this_computer_is_chosen_and_named(app, monkeypatch):  # noqa: F811
    page = _start_page(app, monkeypatch, model="gemma3:4b")
    assert "checked" in _radio(page, "ollama") and "disabled" not in _radio(page, "ollama")
    assert "checked" not in _radio(page, "none")
    assert "Found on your computer: gemma3:4b" in page


def test_an_online_ai_is_never_preselected_and_the_key_is_never_shown(app, monkeypatch):  # noqa: F811
    page = _start_page(app, monkeypatch, openai_key=SECRET)
    cloud = _radio(page, "cloud")
    assert "disabled" not in cloud and "checked" not in cloud
    assert "Key found: OpenAI" in page and "Your key stays in the settings file on your computer" in page
    assert SECRET not in page and SECRET[:12] not in page


def test_old_options_are_gone_and_every_explanation_is_inside_its_box(app, monkeypatch):  # noqa: F811
    page = _start_page(app, monkeypatch)
    for gone in ("ai-auto", 'name="local_only"', 'name="pictures"', "Right now", "Automatic"):
        assert gone not in page
    assert '<p class="lead">Makes PDF files accessible to everyone.</p>' in page
    for box in re.findall(r'<div class="choice">.*?</div></div>', page, flags=re.S):
        ident = re.search(r'id="([^"]+)"', box).group(1)
        assert f'aria-describedby="{ident}-help"' in box and f'id="{ident}-help"' in box
    assert "Runs only on your computer." in page


def test_the_german_page_has_the_same_options(app, monkeypatch):  # noqa: F811
    page = _start_page(app, monkeypatch, model="gemma3:4b", language="de")
    assert "Wählen Sie, wer die Beschreibungen schreibt" in page
    assert "Auf Ihrem Computer gefunden: gemma3:4b" in page and "Läuft nur auf Ihrem Computer." in page


@pytest.mark.parametrize("choice, ai, local", [("ollama", "ollama", True), ("none", "none", True),
                                               ("cloud", "openai", False), ("something-else", "none", True)])
def test_only_the_online_choice_may_send_anything_away(tmp_path, monkeypatch, choice, ai, local):
    monkeypatch.setenv("PDFACCESSGURU_AI", "auto")
    monkeypatch.setenv("PDFACCESSGURU_PRIVACY", "")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    App()._run(Job("j", "test.pdf", "en", tmp_path), {"ai": choice})
    assert os.environ["PDFACCESSGURU_AI"] == ai
    assert (os.environ.get("PDFACCESSGURU_PRIVACY") == "local") is local


def test_the_progress_page_shows_the_percentage_above_the_bar(tmp_path):
    application = App()
    job = Job("j", "test.pdf", "en", tmp_path, fraction=0.42)
    page = application.job_page(job).decode()
    assert page.index('<span id="percent" aria-hidden="true">42%</span>') < page.index("<progress")
    assert "it updates by itself" not in page and "can take a few minutes for long files." in page
    assert 'getElementById("percent").textContent' in page


def test_the_api_key_is_never_part_of_the_settings_text():
    from pdfaccessguru.LLM.client import LLMSettings

    settings = LLMSettings("openai", "https://example.org", SECRET, "model", "model")
    assert SECRET not in repr(settings) and SECRET not in settings.describe()
    assert server_module is not None


def _tour_data(page: str) -> dict:
    import json

    return json.loads(re.search(r"var data = (\{.*?\});\n", page).group(1))


def test_the_tour_starts_by_itself_only_the_first_time_and_can_always_be_opened(app, monkeypatch, tmp_path):  # noqa: F811
    import json

    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"check_for_updates": False}), encoding="utf-8")
    monkeypatch.setattr("pdfaccessguru.updates.settings_file", lambda: settings)
    page = _start_page(app, monkeypatch)
    data = _tour_data(page)
    assert data["auto"] is True and len(data["steps"]) == 6
    for number in range(1, 7):
        assert f'id="tour-{number}"' in page
    assert '<dialog class="tour" id="tour" aria-labelledby="tour-title" aria-describedby="tour-text">' in page
    assert 'id="tour-open"' in page and "Guided tour" in page and "Skip the tour" in page
    assert _request(app, "POST", f"/{app.token}/tour-seen")[0] == 204
    assert json.loads(settings.read_text(encoding="utf-8")) == {"check_for_updates": False, "tour_seen": True}
    assert _tour_data(_start_page(app, monkeypatch))["auto"] is False


def test_the_tour_link_is_on_every_page_and_the_tour_speaks_german(app, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setattr("pdfaccessguru.updates.settings_file", lambda: tmp_path / "settings.json")
    page = _start_page(app, monkeypatch, language="de")
    assert "Rundgang überspringen" in page and _tour_data(page)["steps"][0][0] == "Dateien wählen"
    from pdfaccessguru.webapp.pages import page as make_page

    other = make_page("en", "Result", "<h1>Result</h1>", token="abc").decode()
    assert '<a class="tour-link" id="tour-open" href="/abc/?lang=en&amp;tour=1">Guided tour</a>' in other


def test_a_second_start_shows_the_running_app_instead_of_starting_another(app, monkeypatch, tmp_path):  # noqa: F811
    import json

    from pdfaccessguru.webapp import server

    note = tmp_path / "running-app.json"
    monkeypatch.setattr(server, "_running_app_file", lambda: note)
    opened = []
    monkeypatch.setattr(server.webbrowser, "open", opened.append)
    assert server.open_running_app() is False                       # nothing runs yet
    url = f"http://127.0.0.1:{app.server.server_address[1]}/{app.token}/"
    assert _request(app, "GET", f"/{app.token}/alive")[0] == 204
    note.write_text(json.dumps({"url": url, "pid": 1}))
    assert server.open_running_app() is True and opened == [url]     # the running app is shown again
    note.write_text(json.dumps({"url": "http://127.0.0.1:9/old-key/", "pid": 1}))
    assert server.open_running_app() is False                       # an old note from a stopped app


def test_the_app_leaves_a_note_while_it_runs_and_removes_it_when_closed(monkeypatch, tmp_path):
    import json
    import threading
    import time
    import urllib.request

    from pdfaccessguru.webapp import server

    note = tmp_path / "running-app.json"
    monkeypatch.setattr(server, "_running_app_file", lambda: note)
    monkeypatch.setattr("pdfaccessguru.updates.settings_file", lambda: tmp_path / "settings.json")
    monkeypatch.setenv("PDFACCESSGURU_NO_UPDATE_CHECK", "1")
    thread = threading.Thread(target=server.serve, kwargs={"open_browser": False}, daemon=True)
    thread.start()
    for _ in range(100):
        if note.exists():
            break
        time.sleep(0.05)
    url = json.loads(note.read_text())["url"]
    assert (note.stat().st_mode & 0o777) == 0o600                   # the address holds the app's key
    urllib.request.urlopen(urllib.request.Request(url + "quit", data=b"", method="POST"), timeout=10).read()
    thread.join(timeout=20)
    assert not thread.is_alive() and not note.exists()
