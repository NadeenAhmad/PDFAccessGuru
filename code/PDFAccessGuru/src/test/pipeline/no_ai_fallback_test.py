"""
Phase 4: choosing the AI service, and what every AI task does without one.

No test here needs a real AI: services are simulated, and the fallbacks are what is tested.
"""

from __future__ import annotations

import importlib
import shutil
from pathlib import Path

import pikepdf
import pytest
from pikepdf import Array, Dictionary, Name

from pdfaccessguru.LLM import client
from pdfaccessguru.LLM.client import LLMClient, LLMNotConfigured, settings
from pdfaccessguru.LLM.fallback import detect_language
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.links import describe_links

RESOURCES = Path(__file__).resolve().parents[1] / "resources"


@pytest.fixture
def ai_env(monkeypatch):
    """A clean AI configuration: no keys, no Ollama, nothing chosen."""
    for name in ("PDFACCESSGURU_AI", "PDFACCESSGURU_PRIVACY", "OPENROUTER_API_KEY", "OPENAI_API_KEY",
                 "PDFACCESSGURU_TEXT_MODEL", "PDFACCESSGURU_VISION_MODEL", "DEFAULT_MODEL", "DEFAULT_IMAGE_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(client, "load_environment_variables", lambda: None)
    monkeypatch.setattr(client, "_ollama_models", lambda url: [])
    yield monkeypatch
    settings(refresh=True)


# --- choosing the AI service ---------------------------------------------------------------------

def test_without_keys_or_ollama_no_ai_is_used_and_requests_say_so(ai_env):
    config = settings(refresh=True)
    assert not config.available and "Ollama is not running" in config.reason
    with pytest.raises(LLMNotConfigured):
        LLMClient().send_message("system", "user")


def test_a_key_selects_its_cloud_service(ai_env):
    ai_env.setenv("OPENAI_API_KEY", "test-key")
    config = settings(refresh=True)
    assert config.provider == "openai" and "api.openai.com" in config.url and not config.local


def test_a_running_ollama_is_used_when_no_key_is_set_and_picks_a_picture_model(ai_env):
    ai_env.setattr(client, "_ollama_models", lambda url: ["qwen2.5:14b", "gemma3:4b"])
    config = settings(refresh=True)
    assert config.provider == "ollama" and config.local
    assert config.vision_model == "gemma3:4b" and config.text_model == "gemma3:4b"


def test_privacy_mode_local_never_uses_a_cloud_service(ai_env):
    ai_env.setenv("OPENROUTER_API_KEY", "test-key")
    ai_env.setenv("PDFACCESSGURU_PRIVACY", "local")
    assert not settings(refresh=True).available                     # key ignored, no Ollama
    ai_env.setenv("PDFACCESSGURU_AI", "openrouter")
    config = settings(refresh=True)
    assert not config.available and "privacy" in config.reason


def test_ai_can_be_switched_off(ai_env):
    ai_env.setenv("OPENROUTER_API_KEY", "test-key")
    ai_env.setenv("PDFACCESSGURU_AI", "none")
    assert not settings(refresh=True).available


# --- language ------------------------------------------------------------------------------------

@pytest.mark.parametrize("text, language", [
    ("Die Ergebnisse zeigen deutlich, dass die Methode funktioniert.", "de"),
    ("The results clearly show that the method works for all documents.", "en"),
    ("Figure 3", None), ("", None),
])
def test_language_is_recognised_without_ai_or_left_open_when_unclear(text, language):
    assert detect_language(text) == language


# --- links ---------------------------------------------------------------------------------------

def _pdf_with_links(path: Path) -> Path:
    pdf = pikepdf.new()
    for _ in range(2):
        pdf.add_blank_page(page_size=(612, 792))
    page = pdf.pages[0].obj
    font = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type1, BaseFont=Name.Helvetica))
    page["/Resources"] = Dictionary(Font=Dictionary(F1=font))
    page["/Contents"] = pdf.make_stream(b"BT /F1 12 Tf 72 700 Td (Annual report 2023) Tj ET")
    with_text = Dictionary(Type=Name.Annot, Subtype=Name.Link, Rect=[70, 695, 220, 715],
                           A=Dictionary(S=Name.URI, URI=pikepdf.String("https://www.example.com/report/")))
    to_page = Dictionary(Type=Name.Annot, Subtype=Name.Link, Rect=[70, 500, 90, 510],
                         Dest=Array([pdf.pages[1].obj, Name.Fit]))
    unknown = Dictionary(Type=Name.Annot, Subtype=Name.Link, Rect=[70, 400, 90, 410],
                         A=Dictionary(S=Name.JavaScript, JS=pikepdf.String("app.alert(1)")))
    page["/Annots"] = Array([pdf.make_indirect(with_text), pdf.make_indirect(to_page), pdf.make_indirect(unknown)])
    pdf.save(path)
    return path


def test_links_are_described_by_their_text_and_target_without_ai(tmp_path):
    with pikepdf.open(_pdf_with_links(tmp_path / "links.pdf")) as pdf:
        result = describe_links(pdf)
        texts = [str(annotation.Contents) for annotation in pdf.pages[0].obj.Annots]
    assert texts == ["Annual report 2023 (link to example.com/report)", "Link to page 2", "Link"]
    assert result.described == 3 and result.generic == 1


def test_german_documents_get_german_link_texts(tmp_path):
    with pikepdf.open(_pdf_with_links(tmp_path / "links.pdf")) as pdf:
        pdf.Root["/Lang"] = pikepdf.String("de-DE")
        describe_links(pdf)
        assert str(pdf.pages[0].obj.Annots[1].Contents) == "Link zu Seite 2"


# --- form fields ---------------------------------------------------------------------------------

@pytest.mark.parametrize("name, readable", [
    ("first_name", "First name"), ("txtEmailAddress", "Email address"), ("Text1", ""), ("zip-code", "Zip code"),
])
def test_form_field_names_become_readable_descriptions(name, readable):
    module = importlib.import_module("pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax."
                                     "syntax_correctors_6_florian_walcher.correct_form_field_missing_alt_entry")
    assert module._readable_field_name(name) == readable


# --- the whole pipeline without AI ---------------------------------------------------------------

def test_pipeline_without_ai_describes_pictures_and_says_that_no_ai_was_used(tmp_path, monkeypatch):
    from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
    from pdfaccessguru.pipeline.pipeline import run_pipeline

    monkeypatch.setenv("PDFACCESSGURU_AI", "none")
    source = tmp_path / "figure.pdf"
    shutil.copy(RESOURCES / "veraPDF_corpus/7.3-t01-fail-a.pdf", source)
    report = run_pipeline(str(source), str(tmp_path / "out.pdf"))
    settings(refresh=True)

    from pdfaccessguru.reporting import build_customer_report_markdown

    text = build_customer_report_markdown(report)
    section = text.split("## How Texts Were Written")[1].split("## What Was Found")[0]
    assert "No AI model is used" in section
    assert "Picture descriptions were written from the text in and around each picture" in section
    assert "7.3-1" not in {v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf"))}
