from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import language_utils
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj.language_utils import load_available_language_codes

def test_load_available_language_codes() :
    available_language_codes = load_available_language_codes()
    assert "bm-Nkoo" in available_language_codes
    assert "de-LU" in available_language_codes
    assert "en-001" in available_language_codes


def test_normalize_prompt_text_truncates_long_text():
    normalized = language_utils._normalize_prompt_text("a" * (language_utils.MAX_LANGUAGE_TEXT_LENGTH + 3))

    assert normalized == "a" * language_utils.MAX_LANGUAGE_TEXT_LENGTH


def test_choose_language_for_text_uses_document_text_fallback(monkeypatch):
    """No text of its own: the document's text decides, by word statistics (no AI needed)."""
    calls = []
    monkeypatch.setattr(language_utils, "determine_lang_tag", lambda text: calls.append(text) or None)
    monkeypatch.setattr(language_utils, "extract_text_from_document",
                        lambda pdf: "Hello from the document. The results clearly show that the method works.")
    assert language_utils.choose_language_for_text(None, None, None) == "en"
    assert calls == []                                    # the AI was not needed


def test_choose_language_asks_the_ai_only_for_unclear_text(monkeypatch):
    import pdfaccessguru.LLM.fallback as fallback
    calls = []
    monkeypatch.setattr(fallback, "ai_available", lambda: True)
    monkeypatch.setattr(language_utils, "determine_lang_tag", lambda text: calls.append(text) or "fr")
    assert language_utils.choose_language_for_text("Ciao!", None, None) == "fr"     # too short for statistics
    assert calls == ["Ciao!"]
