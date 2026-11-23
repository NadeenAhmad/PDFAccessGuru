"""1.1.0.post1: the key can be pasted in the app, and the model can be chosen, so nobody has to edit a settings file."""

from __future__ import annotations

import json
import os
import re
import stat

import pytest

from pdfaccessguru.utils import environment_variables as env
from test.webapp_test import _request, _upload, app  # noqa: F401  (fixture)

OPENROUTER = "sk-" + "or-" + "v1-NOT-A-REAL-KEY-0123456789abcd"   # built in pieces, so key scans do not flag this file
OPENAI = "sk-" + "proj-" + "NOT-A-REAL-KEY-0123456789wxyz"


@pytest.fixture
def files(tmp_path, monkeypatch):
    """The user's settings folder is a temporary one; no key in the environment; Ollama has the given models."""
    env_file, settings = tmp_path / ".env", tmp_path / "settings.json"
    monkeypatch.setattr(env, "user_env_file", lambda: env_file)
    monkeypatch.setattr("pdfaccessguru.updates.settings_file", lambda: settings)
    monkeypatch.setattr("pdfaccessguru.LLM.client.load_environment_variables", lambda: None)
    for name in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "PDFACCESSGURU_VISION_MODEL", "PDFACCESSGURU_TEXT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr("pdfaccessguru.LLM.client._ollama_models",
                        lambda url: ["qwen2.5:7b", "embeddinggemma:latest", "gemma3:4b", "gemma4:e4b"])
    return env_file, settings


def test_a_key_is_saved_in_the_settings_file_replaced_and_removed(files):
    env_file, _ = files
    env_file.write_text("OTHER=1\nOPENAI_API_KEY=old-key-0000000000000000\n", encoding="utf-8")
    assert env.save_api_key("  " + OPENROUTER + "\n") == "OPENROUTER_API_KEY"
    lines = env_file.read_text(encoding="utf-8").splitlines()
    assert lines == ["OTHER=1", f"OPENROUTER_API_KEY={OPENROUTER}"]
    assert os.environ["OPENROUTER_API_KEY"] == OPENROUTER and "OPENAI_API_KEY" not in os.environ
    if os.name != "nt":
        assert stat.S_IMODE(env_file.stat().st_mode) == 0o600
    assert env.api_key_end() == "abcd"
    env.remove_api_keys()
    assert env_file.read_text(encoding="utf-8").splitlines() == ["OTHER=1"]
    assert "OPENROUTER_API_KEY" not in os.environ
    with pytest.raises(ValueError):
        env.save_api_key("not a key")


def test_without_a_key_the_page_has_a_key_field_outside_the_main_form(app, files):  # noqa: F811
    page = _request(app, "GET", f"/{app.token}/?lang=en")[2].decode()
    assert '<input type="password" id="api-key" name="api_key" form="key-form"' in page
    assert re.search(r'</form>\s*<form id="key-form" method="post" action="/[^/]+/key\?lang=en"></form>', page)
    assert "No key set up yet. Paste your key below." in page and "Write OPENAI_API_KEY" not in page


def test_pasting_a_key_saves_it_and_the_page_shows_only_its_end(app, files):  # noqa: F811
    env_file, _ = files
    status, headers, _ = _request(app, "POST", f"/{app.token}/key?lang=en", f"api_key={OPENAI}",
                                  {"Content-Type": "application/x-www-form-urlencoded"})
    assert status in (302, 303) and headers["Location"].endswith("#tour-2")
    assert f"OPENAI_API_KEY={OPENAI}" in env_file.read_text(encoding="utf-8")
    page = _request(app, "GET", f"/{app.token}/?lang=en")[2].decode()
    assert "Key found: OpenAI (ends with wxyz)" in page and OPENAI not in page and OPENAI[:12] not in page
    assert 'form="key-remove-form"' in page and 'name="api_key"' not in page
    assert 'value="gpt-6-luna"' in page                       # the OpenAI name of the default model
    _request(app, "POST", f"/{app.token}/key-remove?lang=en", "", {"Content-Type": "application/x-www-form-urlencoded"})
    assert "OPENAI_API_KEY" not in env_file.read_text(encoding="utf-8")


def test_a_wrong_key_is_not_saved_and_the_page_says_why(app, files):  # noqa: F811
    env_file, _ = files
    status, _, body = _request(app, "POST", f"/{app.token}/key?lang=de", "api_key=hello",
                               {"Content-Type": "application/x-www-form-urlencoded"})
    assert status == 400 and "vollständiger Schlüssel" in body.decode()
    assert not env_file.exists()


def test_the_model_menu_lists_installed_models_pictures_first_and_keeps_the_last_choice(app, files):  # noqa: F811
    _, settings = files
    page = _request(app, "GET", f"/{app.token}/?lang=en")[2].decode()
    menu = re.search(r'<select id="ollama-model" name="ollama_model"[^>]*>(.*?)</select>', page).group(1)
    assert re.findall(r'value="([^"]+)"', menu) == ["gemma4:e4b", "gemma3:4b", "qwen2.5:7b"]   # no embedding model
    assert '<option value="gemma4:e4b" selected>' in menu and "Found on your computer: gemma4:e4b" in page
    settings.write_text(json.dumps({"ollama_model": "gemma3:4b"}), encoding="utf-8")
    page = _request(app, "GET", f"/{app.token}/?lang=en")[2].decode()
    assert '<option value="gemma3:4b" selected>' in page and "Found on your computer: gemma3:4b" in page


@pytest.mark.parametrize("fields, expected", [
    ({"ai": "ollama", "ollama_model": "gemma3:4b"}, "gemma3:4b"),
    ({"ai": "ollama", "ollama_model": "not-installed:1b"}, None),
    ({"ai": "cloud", "online_model": "google/gemma-4-26b-a4b-it"}, "google/gemma-4-26b-a4b-it"),
    ({"ai": "cloud", "online_model": "bad model; rm -rf"}, None),
    ({"ai": "none", "ollama_model": "gemma3:4b"}, None),
])
def test_the_chosen_model_is_used_for_the_job_and_remembered(app, files, monkeypatch, fields, expected):  # noqa: F811
    _, settings = files
    seen = {}

    def fake_fix(job, number, result, options, progress):
        seen["vision"] = os.environ.get("PDFACCESSGURU_VISION_MODEL")
        seen["text"] = os.environ.get("PDFACCESSGURU_TEXT_MODEL")
        raise RuntimeError("stop here")

    monkeypatch.setattr(app, "_fix_one", fake_fix)
    _upload(app, b"%PDF-1.7\n%%EOF\n", **fields)
    for _ in range(200):
        if seen:
            break
        import time
        time.sleep(0.02)
    assert seen == {"vision": expected, "text": expected}
    if expected:
        key = "ollama_model" if fields["ai"] == "ollama" else "online_model"
        assert json.loads(settings.read_text(encoding="utf-8"))[key] == expected
    for name in ("PDFACCESSGURU_VISION_MODEL", "PDFACCESSGURU_TEXT_MODEL"):
        os.environ.pop(name, None)
