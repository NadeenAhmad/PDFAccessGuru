"""
What the tool does when no AI model is available (Phase 4), and how it tells the user.

Every task that can use an AI also works without one. The simple method is used, and the report
says once per task, in plain words, what was done instead, so the user knows which texts to
check. Some tasks use the simple method first even with an AI, because it is reliable and fast
(e.g. the language of long text).
"""

from __future__ import annotations

from functools import lru_cache

from pdfaccessguru.LLM.client import settings
from pdfaccessguru.pipeline.reporting.writer import report_info, report_warn

# What the report says when a task had to do without an AI (one sentence each).
FALLBACK_NOTES = {
    "language": "The language of some short texts could not be recognised without an AI model, "
                "so the language of the whole document was used for them.",
    "alt_text": "Picture descriptions were written from the text in and around each picture, "
                "without an AI model. Please check them.",
    "link_text": "Link descriptions were made from each link's text or address, without an AI model.",
    "title": "The document title was taken from its first heading or first line, without an AI model.",
    "unicode": "Some characters could not be identified without an AI model; they are listed as still open.",
    "form_field": "Form field descriptions were made from the field names, without an AI model. Please check them.",
    "formula": "Formula descriptions were made from the text of each formula, without an AI model. Please check them.",
    "table": "Some table rows could not be worked out without an AI model; they are listed as still open.",
}

_noted: set[str] = set()


def ai_available() -> bool:
    return settings().available


def start_run() -> None:
    """Called at the start of each run: report which AI is used, and forget earlier notes."""
    _noted.clear()
    config = settings(refresh=True)
    if config.available:
        report_info(f"Texts such as picture descriptions are written by: {config.describe()}.")
    else:
        report_warn(
            f"No AI model is used ({config.reason}). Picture descriptions, link texts and similar "
            "texts are written with simple rules instead, which can be less helpful. To use an AI, "
            "install Ollama (a free AI that runs on this computer), or add a key for an online AI like "
            "ChatGPT (OpenAI) or OpenRouter; "
            "'pdfaccessguru doctor' shows how.")


def note_fallback(task: str) -> None:
    """Say once per run that a task was done without an AI."""
    if task in _noted:
        return
    _noted.add(task)
    report_info("Without AI: " + FALLBACK_NOTES.get(task, f"{task} was done with simple rules."))


@lru_cache(maxsize=1)
def _language_identifier():
    from py3langid.langid import MODEL_FILE, LanguageIdentifier
    return LanguageIdentifier.from_model_file(MODEL_FILE, norm_probs=True)


def detect_language(text: str | None, min_confidence: float = 0.9) -> str | None:
    """
    The language of a text as a language tag ("de", "en", ...), or None if the text is too
    short or the result is not clear enough. Works without an AI (word and letter statistics).
    """
    if not text:
        return None
    letters = sum(char.isalpha() for char in text)
    if letters < 12:
        return None
    language, confidence = _language_identifier().classify(text[:5000])
    return language if confidence >= min_confidence else None


# German versions of the notes above, for German reports (Phase 7a).
_NOTES_DE = {
    "language": "Die Sprache einiger kurzer Texte ließ sich ohne KI-Modell nicht erkennen; für sie wurde die "
                "Sprache des ganzen Dokuments verwendet.",
    "alt_text": "Bildbeschreibungen wurden ohne KI-Modell aus dem Text in und um jedes Bild erstellt. Bitte prüfen Sie sie.",
    "link_text": "Linkbeschreibungen wurden ohne KI-Modell aus dem Text oder der Adresse jedes Links erstellt.",
    "title": "Der Dokumenttitel wurde ohne KI-Modell aus der ersten Überschrift oder ersten Zeile übernommen.",
    "unicode": "Einige Zeichen ließen sich ohne KI-Modell nicht bestimmen; sie stehen bei den offenen Problemen.",
    "form_field": "Beschreibungen von Formularfeldern wurden ohne KI-Modell aus den Feldnamen erstellt. Bitte prüfen Sie sie.",
    "formula": "Formelbeschreibungen wurden ohne KI-Modell aus dem Text jeder Formel erstellt. Bitte prüfen Sie sie.",
    "table": "Einige Tabellenzeilen ließen sich ohne KI-Modell nicht bestimmen; sie stehen bei den offenen Problemen.",
}


def translate_note(message: str) -> str:
    """The German version of a note or status line written by this module (else unchanged)."""
    for key, english in FALLBACK_NOTES.items():
        if message == english:
            return _NOTES_DE[key]
    if message.startswith("Texts such as picture descriptions are written by: "):
        who = message[len("Texts such as picture descriptions are written by: "):].rstrip(".")
        who = who.replace("on this computer", "auf diesem Computer").replace("in the cloud", "in der Cloud").replace("model", "Modell")
        return f"Texte wie Bildbeschreibungen schreibt: {who}."
    if message.startswith("No AI model is used"):
        return ("Es wird kein KI-Modell verwendet. Bildbeschreibungen, Linktexte und ähnliche Texte werden "
                "stattdessen mit einfachen Regeln erstellt, die weniger hilfreich sein können. Für eine KI "
                "installieren Sie Ollama (eine kostenlose KI, die auf diesem Computer läuft) oder hinterlegen "
                "einen Schlüssel für eine Online-KI wie ChatGPT (OpenAI) oder OpenRouter; 'pdfaccessguru doctor' zeigt, wie.")
    return message
