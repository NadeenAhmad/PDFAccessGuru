"""1.0.3: current default models, Gemma 4 first on this computer, and settings a model refuses."""

from __future__ import annotations

import pytest

from pdfaccessguru.LLM import client
from pdfaccessguru.LLM.client import LLMClient, LLMSettings, settings
from test.pipeline.no_ai_fallback_test import ai_env  # noqa: F401  (fixture)


def test_gemma_4_is_chosen_before_gemma_3(ai_env):  # noqa: F811
    ai_env.setattr(client, "_ollama_models", lambda url: ["qwen2.5:14b", "gemma3:4b", "gemma4:e4b"])
    config = settings(refresh=True)
    assert config.vision_model == "gemma4:e4b" and config.text_model == "gemma4:e4b"
    assert client.local_model() == "gemma4:e4b"


@pytest.mark.parametrize("key, model", [("OPENAI_API_KEY", "gpt-6-luna"), ("OPENROUTER_API_KEY", "openai/gpt-6-luna")])
def test_an_online_key_uses_gpt_6_luna(ai_env, key, model):  # noqa: F811
    ai_env.setenv(key, "test-key")
    config = settings(refresh=True)
    assert config.text_model == model and config.vision_model == model


class _Answer:
    def __init__(self, status: int, text: str = ""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(self.text)

    def json(self):
        return {"choices": [{"message": {"content": "A bar chart."}}]}


def _record(monkeypatch, answers):
    sent = []

    def post(url, headers, json, timeout):
        sent.append(dict(json))
        return answers.pop(0)
    monkeypatch.setattr(client.requests, "post", post)
    monkeypatch.setattr(client, "_REFUSED", {})
    return sent


def test_a_model_that_refuses_the_temperature_is_asked_again_without_it(monkeypatch):
    cloud = LLMSettings("openai", "https://example.org", "test-key", "new-model", "new-model")
    sent = _record(monkeypatch, [_Answer(400, "Unsupported value: 'temperature' does not support 0.2"),
                                 _Answer(200), _Answer(200)])
    assert LLMClient(cloud).send_message("system", "user") == "A bar chart."
    assert "temperature" in sent[0] and "temperature" not in sent[1]
    LLMClient(cloud).send_message("system", "user")
    assert "temperature" not in sent[2]                              # remembered, no second refusal
    assert all("reasoning_effort" not in request for request in sent)   # online models keep their own setting


def test_local_models_answer_without_thinking_and_other_errors_are_not_retried(monkeypatch):
    local = LLMSettings("ollama", "http://localhost:11434/v1/chat/completions", "ollama", "gemma4:e4b", "gemma4:e4b")
    sent = _record(monkeypatch, [_Answer(200), _Answer(400, "bad request")])
    LLMClient(local).send_message("system", "user")
    assert sent[0]["reasoning_effort"] == "none" and sent[0]["temperature"] == 0.2
    with pytest.raises(client.OpenRouterConnectionFailedException):
        LLMClient(local).send_message("system", "user")
    assert len(sent) == 2


def test_tests_never_read_the_installed_tools_settings_file():
    import os

    from pdfaccessguru.utils import environment_variables

    environment_variables.load_environment_variables()
    assert not environment_variables.user_env_file().exists()
    assert not os.environ.get("OPENROUTER_API_KEY", "").startswith("sk-or-") or (
        environment_variables.Path(__file__).resolve().parents[3] / ".env").is_file()   # developer's own file only


@pytest.mark.parametrize("written, spoken", [
    (r"Flow diagram: PDF file $\rightarrow$ Tags $\rightarrow$ Screen reader", "Flow diagram: PDF file → Tags → Screen reader"),
    (r"Temperatures stay $\leq 30^{\circ}$C", "Temperatures stay ≤ 30°C"),
    (r"**Bar chart** of sales, 10 \% higher", "Bar chart of sales, 10 % higher"),
    ("Prices rose from $5 to $10 in 2024.", "Prices rose from $5 to $10 in 2024."),     # money stays
    ("Logo of the University of Stuttgart", "Logo of the University of Stuttgart"),
])
def test_maths_notation_and_markdown_become_plain_text_for_screen_readers(written, spoken):
    from pdfaccessguru.LLM.output_checks import spoken_text

    assert spoken_text(written) == spoken
