"""Phase 7b: the report follows the language of the PDF, for any language."""

from __future__ import annotations

import json
from collections import Counter

import pymupdf as fitz
import pikepdf
import pytest

from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.reporting import report_language as rl
from pdfaccessguru.reporting.pdf_report import render_report_pdf

REPORT = """# Accessibility Report

File: lecture.pdf

## Result

Some problems were fixed. The rest are listed below under “What Is Still Open”.

- Passes the automatic check: No
- Problems fixed: 12

| Problem | How often | What you can do |
|---|---:|---|
| Picture without a description | 3 | Run 'pdfaccessguru doctor' to set up an AI. |

- Page 2. The tool wrote: “Diagram of the network”
"""


@pytest.fixture(autouse=True)
def own_cache(tmp_path, monkeypatch):
    # only the translations go to a test folder; the helper programs (veraPDF) must stay findable
    monkeypatch.setattr(rl, "_cache_file", lambda language: tmp_path / "translations" / f"{language}.json")


def _pdf_with_language(path, tag, text="Hello"):
    document = fitz.open()
    document.new_page().insert_text((72, 72), text)
    document.save(path)
    if tag is not None:
        with pikepdf.open(path, allow_overwriting_input=True) as pdf:
            pdf.Root.Lang = pikepdf.String(tag)
            pdf.save(path)
    return path


def test_the_report_language_is_the_language_of_the_pdf(tmp_path):
    assert rl.report_language(_pdf_with_language(tmp_path / "a.pdf", "en-GB")) == "en"
    assert rl.report_language(_pdf_with_language(tmp_path / "b.pdf", "ar-EG")) == "ar"
    german = "Die Vorlesung behandelt die Grundlagen der Informatik und die Programmierung in Python."
    assert rl.report_language(_pdf_with_language(tmp_path / "c.pdf", None, german)) == "de"
    assert rl.report_language(_pdf_with_language(tmp_path / "d.pdf", "x-unknown")) == "en"


def test_without_an_ai_the_report_stays_english_and_says_why(monkeypatch):
    monkeypatch.setattr("pdfaccessguru.LLM.fallback.ai_available", lambda: False)
    text, note = rl.translate_markdown(REPORT, "ar")
    assert text == REPORT
    assert "in English" in note and "Arabic" in note


def test_translation_keeps_quotes_commands_and_tables_and_is_cached(monkeypatch):
    monkeypatch.setattr("pdfaccessguru.LLM.fallback.ai_available", lambda: True)
    calls = []

    def fake_ai(texts, language):
        calls.append(len(texts))
        return [f"[{language}] {text}" for text in texts]

    monkeypatch.setattr(rl, "_ask_ai", fake_ai)
    text, note = rl.translate_markdown(REPORT, "fr")
    assert note is None
    assert "# [fr] Accessibility Report" in text
    assert "“Diagram of the network”" in text and "'pdfaccessguru doctor'" in text and "lecture.pdf" in text
    assert "| [fr] Picture without a description | 3 | [fr] Run 'pdfaccessguru doctor' to set up an AI. |" in text
    assert "|---|---:|---|" in text
    assert calls
    cache = json.loads(rl._cache_file("fr").read_text(encoding="utf-8"))
    assert cache["Picture without a description"] == "[fr] Picture without a description"
    calls.clear()
    assert rl.translate_markdown(REPORT, "fr")[0] == text and calls == []        # all from the cache


def test_a_translation_that_loses_a_quote_is_not_used(monkeypatch):
    monkeypatch.setattr("pdfaccessguru.LLM.fallback.ai_available", lambda: True)
    monkeypatch.setattr(rl, "_ask_ai", lambda texts, language: ["(lost)" for _ in texts])
    text, note = rl.translate_markdown("- Page 2. The tool wrote: “Diagram”\n", "es")
    assert text == "- Page 2. The tool wrote: “Diagram”\n" and "stay in English" in note


@pytest.mark.parametrize("language, title, sample", [
    ("en", "Accessibility Report", REPORT),
    ("ru", "Отчёт о доступности", "# Отчёт о доступности\n\nВсе проблемы исправлены.\n\n| Проблема | Число |\n|---|---:|\n| Рисунок | 3 |\n"),
    ("ar", "تقرير إمكانية الوصول", "# تقرير إمكانية الوصول\n\nتم إصلاح جميع المشاكل.\n"),
])
def test_the_pdf_report_is_tagged_in_its_language_and_shows_every_script(tmp_path, language, title, sample):
    data = render_report_pdf(sample, title, language=language)
    (tmp_path / "report.pdf").write_bytes(data)
    with pikepdf.open(tmp_path / "report.pdf") as pdf:
        assert str(pdf.Root.Lang) == language and "/StructTreeRoot" in pdf.Root
    with fitz.open(tmp_path / "report.pdf") as document:
        fonts = " ".join(font[3] for page in document for font in page.get_fonts())
    if language == "ar":
        assert "Arabic" in fonts                       # drawn with a font that has Arabic letters
    else:                                              # Latin and Cyrillic: passes the PDF/UA check
        rules = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "report.pdf")))
        assert not rules, rules


def test_rtl_languages_are_marked():
    assert rl.text_direction("ar") == "rtl" and rl.text_direction("he") == "rtl" and rl.text_direction("de") == "ltr"


def test_joined_scripts_get_their_exact_text_for_screen_readers():
    """Arabic letters join when drawn; each tagged text element carries the exact letters as ActualText."""
    import io

    from pdfaccessguru.reporting.pdf_report import _elements

    sample = ("# تقرير إمكانية الوصول\n\n## النتيجة\n\nتم إصلاح جميع المشاكل.\n\n- يجتاز الفحص التلقائي: نعم\n\n"
              "| المشكلة | العدد |\n|---|---:|\n| صورة بدون وصف | 3 |\n")
    with pikepdf.open(io.BytesIO(render_report_pdf(sample, "تقرير", language="ar"))) as pdf:
        texts = [str(element.ActualText) for element in _elements(pdf)
                 if str(element.S).lstrip("/") in ("H1", "H2", "P", "LBody", "TD", "TH")]
    joined = " ".join(texts)
    for sentence in ("تقرير إمكانية الوصول", "تم إصلاح جميع المشاكل.", "يجتاز الفحص التلقائي: نعم", "صورة بدون وصف"):
        assert sentence in joined
    assert len(texts) >= 6
