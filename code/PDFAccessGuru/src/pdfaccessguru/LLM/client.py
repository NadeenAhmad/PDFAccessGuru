"""
One connection to a language model, for three kinds of service (Phase 4):

- OpenRouter (cloud, key: OPENROUTER_API_KEY)
- OpenAI (cloud, key: OPENAI_API_KEY)
- Ollama (runs on this computer, nothing leaves it; https://ollama.com)

All three speak the same "chat completions" format, so one client serves them. Which one is
used is set with PDFACCESSGURU_AI (openrouter, openai, ollama, none or auto). With "auto" (the
default) a configured key is used, otherwise a running Ollama, otherwise no AI.
PDFACCESSGURU_PRIVACY=local allows only Ollama, so no document content is ever sent away.

Without an AI every task falls back to simple rules (see LLM/fallback.py) and the report says so.
"""

from __future__ import annotations

import base64
import os
from collections import Counter
from dataclasses import dataclass

import requests

from pdfaccessguru.exceptions.llm_exceptions.open_router_connection_failed_exception import (
    OpenRouterConnectionFailedException,
)
from pdfaccessguru.utils.environment_variables import load_environment_variables

PROVIDERS = ("openrouter", "openai", "ollama")
_CLOUD_URLS = {
    "openrouter": "https://openrouter.ai/api/v1/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
}
_DEFAULT_MODELS = {
    "openrouter": ("google/gemma-4-26b-a4b-it", "google/gemma-4-26b-a4b-it"),
    "openai": ("gpt-4.1-mini", "gpt-4.1-mini"),
}
# Ollama models that can read pictures, best first; text tasks use the first installed model.
_OLLAMA_VISION = ("gemma3", "qwen2.5vl", "llama3.2-vision", "llava", "minicpm-v")
_OLLAMA_TEXT = ("gemma3", "qwen2.5", "llama3", "mistral")


class LLMNotConfigured(OpenRouterConnectionFailedException):
    """No language model is set up (or none that can do this task). Use the fallback."""


@dataclass(frozen=True)
class LLMSettings:
    provider: str               # one of PROVIDERS, or "none"
    url: str = ""
    api_key: str = ""
    text_model: str = ""
    vision_model: str = ""      # "" if the service has no model that reads pictures
    reason: str = ""            # why no AI is used (plain language)

    @property
    def available(self) -> bool:
        return self.provider in PROVIDERS

    @property
    def local(self) -> bool:
        return self.provider == "ollama"

    def describe(self, language: str = "en") -> str:
        """Plain-language description for reports, the doctor command and the app (English or German)."""
        german = language == "de"
        if not self.available:
            return f"kein KI-Modell ({_reason_de(self.reason)})" if german else f"no AI model ({self.reason})"
        name = {"openrouter": "OpenRouter", "openai": "OpenAI", "ollama": "Ollama"}[self.provider]
        if german:
            return f"{name} {'auf diesem Computer' if self.local else 'in der Cloud'}, Modell {self.text_model}"
        return f"{name} {'on this computer' if self.local else 'in the cloud'}, model {self.text_model}"


_REASONS_DE = {
    "Ollama is not running or has no model installed": "Ollama läuft nicht oder hat kein Modell installiert",
    "AI is switched off": "KI ist ausgeschaltet",
    "no AI key is set and Ollama is not running": "kein KI-Schlüssel eingerichtet und Ollama läuft nicht",
    "no OpenRouter key is set": "kein OpenRouter-Schlüssel eingerichtet",
    "no OpenAI key is set": "kein OpenAI-Schlüssel eingerichtet",
}


def _reason_de(reason: str) -> str:
    if reason in _REASONS_DE:
        return _REASONS_DE[reason]
    if reason.startswith("privacy mode 'local' does not allow "):
        return f"der Datenschutzmodus „lokal“ erlaubt {reason.rsplit(' ', 1)[-1]} nicht"
    return reason


def _ollama_url() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def _ollama_models(url: str) -> list[str]:
    try:
        response = requests.get(f"{url}/api/tags", timeout=1.5)
        response.raise_for_status()
        return [model["name"] for model in response.json().get("models", [])]
    except (requests.RequestException, ValueError, KeyError):
        return []


def _pick(installed: list[str], preferred: tuple[str, ...]) -> str:
    for family in preferred:
        for name in installed:
            if name.split(":")[0] == family:
                return name
    return ""


def _ollama_settings() -> LLMSettings:
    url = _ollama_url()
    installed = _ollama_models(url)
    if not installed:
        return LLMSettings("none", reason="Ollama is not running or has no model installed")
    vision = os.environ.get("PDFACCESSGURU_VISION_MODEL") or _pick(installed, _OLLAMA_VISION)
    text = os.environ.get("PDFACCESSGURU_TEXT_MODEL") or _pick(installed, _OLLAMA_TEXT) or installed[0]
    return LLMSettings("ollama", f"{url}/v1/chat/completions", "ollama", text, vision)


def _cloud_settings(provider: str) -> LLMSettings:
    key = os.environ.get("OPENROUTER_API_KEY" if provider == "openrouter" else "OPENAI_API_KEY", "")
    if not key:
        return LLMSettings("none", reason=f"no {'OpenRouter' if provider == 'openrouter' else 'OpenAI'} key is set")
    text, vision = _DEFAULT_MODELS[provider]
    if provider == "openrouter":                       # the names used before Phase 4 still work
        text = os.environ.get("DEFAULT_MODEL", text)
        vision = os.environ.get("DEFAULT_IMAGE_MODEL", vision)
    text = os.environ.get("PDFACCESSGURU_TEXT_MODEL", text)
    vision = os.environ.get("PDFACCESSGURU_VISION_MODEL", vision)
    return LLMSettings(provider, _CLOUD_URLS[provider], key, text, vision)


_settings: LLMSettings | None = None
usage: Counter = Counter()          # requests per kind ("text", "picture") in this run


def settings(refresh: bool = False) -> LLMSettings:
    """The language model to use, from PDFACCESSGURU_AI, PDFACCESSGURU_PRIVACY and the keys."""
    global _settings
    if _settings is not None and not refresh:
        return _settings
    load_environment_variables()
    choice = os.environ.get("PDFACCESSGURU_AI", "auto").strip().lower() or "auto"
    local_only = os.environ.get("PDFACCESSGURU_PRIVACY", "").strip().lower() == "local"
    if choice == "none":
        result = LLMSettings("none", reason="AI is switched off")
    elif local_only and choice not in ("auto", "ollama"):
        result = LLMSettings("none", reason=f"privacy mode 'local' does not allow {choice}")
    elif choice == "ollama" or (local_only and choice == "auto"):
        result = _ollama_settings()
    elif choice in ("openrouter", "openai"):
        result = _cloud_settings(choice)
    else:                                               # auto: a key, else a running Ollama
        result = next((s for s in (_cloud_settings("openrouter"), _cloud_settings("openai")) if s.available), None) \
            or _ollama_settings()
        if not result.available:
            result = LLMSettings("none", reason="no AI key is set and Ollama is not running")
    _settings = result
    return result


class LLMClient:
    """
    Sends prompts to the configured model. Both methods return the answer text and raise
    LLMNotConfigured if no (suitable) model is set up, or OpenRouterConnectionFailedException
    if the request fails. (The class keeps the name OpenRouterBaseProvider as an alias.)
    """

    def __init__(self, config: LLMSettings | None = None):
        self.config = config or settings()

    def _post(self, model: str, messages: list, json_mode: bool, kind: str) -> str:
        if not self.config.available:
            raise LLMNotConfigured(self.config.reason)
        payload = {"model": model, "messages": messages, "temperature": 0.2}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}
        timeout = (5, 600) if self.config.local else (15, 180)    # local models run on the processor
        try:
            response = requests.post(self.config.url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            usage[kind] += 1
            return response.json()["choices"][0]["message"]["content"] or ""
        except (requests.RequestException, ValueError, KeyError, IndexError) as error:
            raise OpenRouterConnectionFailedException(str(error)) from error

    def send_message(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        return self._post(self.config.text_model, messages, json_mode, "text")

    def send_message_with_image(self, system_prompt: str, user_prompt: str, image_path, json_mode: bool = False) -> str:
        if self.config.available and not self.config.vision_model:
            raise LLMNotConfigured("the AI model cannot read pictures")
        data_url = "data:image/png;base64," + base64.b64encode(image_path.image_data).decode("ascii")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text", "text": user_prompt},
                                         {"type": "image_url", "image_url": {"url": data_url}}]},
        ]
        return self._post(self.config.vision_model, messages, json_mode, "picture")
