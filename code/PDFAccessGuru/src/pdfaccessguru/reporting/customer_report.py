"""
Customer report: a short, plain-language summary for the person who owns the PDF.

Writing rules for every text in this report: short sentences, everyday words, no file
paths or internal names unless needed, and always say what the reader can do next.
Technical details (context paths, logs, raw data) belong in the technical report.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import DISABLED_CORRECTORS
from pdfaccessguru.reporting.report_metrics import ReportMetrics, ViolationMetric, build_report_metrics
from pdfaccessguru.reporting.review_list import build_review_groups, estimated_minutes, review_list_images, review_list_markdown
from pdfaccessguru.reporting.pdf_report import render_report_pdf
from pdfaccessguru.reporting.plain_language import plain_name, problem_meaning, problem_todo, rule_id_of
from pdfaccessguru.reporting.report_language import BUILT_IN, report_language, translate_markdown

_MAX_PAGES_LISTED = 12

# Every sentence of the report in English and German (Phase 7a).
TEXT = {
    "en": {
        "title": "Accessibility Report", "file": "File", "new_file": "New file", "result": "Result",
        "numbers": "In Numbers", "passes": "Passes the automatic check", "yes": "Yes", "no": "No",
        "readable": "Text that assistive technologies can read", "found": "Problems found", "fixed": "Problems fixed",
        "open": "Problems still open", "to_check": "Texts the tool wrote for you to review",
        "on_purpose": "Not fixed on purpose", "see_below": " (see below why)",
        "good_to_know": "Good to know: one problem is often counted many times, for example once for every line "
                        "of text. So the number of problems does not show how much work is left. Passing the "
                        "automatic check is a good sign, but a person should still review the reading order and the texts.",
        "what_found": "What Was Found",
        "table_found": "| Problem | Found | Fixed | Still open | What it means |",
        "what_open": "What Is Still Open",
        "open_intro": "These problems must be fixed by hand, for example in the program you used to make the PDF.",
        "table_open": "| Problem | How often | Where | What you can do |",
        "not_fixed": "Not Fixed on Purpose",
        "not_fixed_intro": "The tool could have made these problems disappear from the check, but only by making "
                           "the file worse for people who use screen readers or other assistive technologies. So it did not touch them. They need "
                           "to be fixed by hand.",
        "table_not_fixed": "| Problem | How often | Why it was not fixed |",
        "unknown": "unknown", "before_after": "{before} before, {after} after", "none": "none",
        "minutes": "about {n} minute{s}", "review_on": "{items} (takes {time}, see the list below)",
        "review_off": "{items} (takes {time}; turn on “Add a review list to the report” to see them)",
        "review_done": "none left: you reviewed them in the app",
        "yours_title": "Your Changes",
        "yours_intro": "You reviewed what the tool did and corrected it in the app. The new PDF contains your changes.",
        "yours_changed": "{what}: changed by you to “{new}” (the tool wrote “{old}”)",
        "yours_reviewed": "{what}: reviewed by you",
        "yours_shown": "Pictures you showed again with a description: {n}",
        "one_title": "Title", "one_language": "Language", "one_images": "Picture description",
        "one_formulas": "Formula description", "one_links": "Link description", "one_forms": "Form field description",
        "all_images": "Picture descriptions", "all_formulas": "Formula descriptions", "all_links": "Link descriptions",
        "all_forms": "Form field descriptions",
        "on_page": "{what} on page {page}",
        "new": "{n} new", "page": "page", "pages": "pages", "and_more": " and {n} more", "whole": "whole document",
        "untagged": "Most of the text in this file has no tags. Without tags, assistive technologies such as screen readers cannot present the file "
                    "well.\n\nWhat you can do: open the original file in Word. Choose File > Save As > PDF > Options "
                    "and turn on “Document structure tags for accessibility”. Save the PDF and run "
                    "PDFAccessGuru again.",
        "no_problems": "The automatic check found no problems.",
        "all_fixed": "All problems that the automatic check found are fixed.",
        "some_fixed": "Some problems were fixed. The rest are listed below under “What Is Still Open”.",
        "none_fixed": "The tool could not fix the problems in this file. They are listed below.",
        "ai_title": "How Texts Were Written",
        "would_harm": "The automatic fix would make the file worse for people who use assistive technologies.",
        "contrast": "Text with too little contrast",
        "contrast_fixed_short": "{n} (fixed: {fixed})",
        "contrast_title": "Colour Contrast",
        "contrast_ok": "All text that could be measured has enough contrast with its background (WCAG 2.2, 1.4.3, level AA).",
        "contrast_off": "Places with too little contrast between the text and its background (WCAG 2.2, 1.4.3, level AA): {n}, on {pages}. The colours were not changed, because the option “Improve colour contrast” was off. Turn it on if the colours of this file may change. For templates with fixed colours, ask the owner of the template.",
        "contrast_fixed": "Places with too little contrast whose text colour was made just dark or light enough, keeping its hue: {n}. Nothing else was changed.",
        "contrast_left": "Places that still have too little contrast: {n}, on {pages}. Their text colour could not be changed safely (for example white text on a mid-tone background needs a different background). Please fix them in the original file.",
        "contrast_unclear": "Text on pictures or colour gradients, whose contrast cannot be measured automatically: {n}. Please look at it yourself.",
        "contrast_undone": "The colour changes were undone, because they would have changed more than the colours.",
        "contrast_example": "Examples:",
        "meaning_title": "Meaning and Structure",
        "meaning_intro": "These checks go beyond the automatic PDF/UA check.",
        "meaning_ok": "No problems with meaning or structure were found.",
        "meaning_fixed": "Fixed:",
        "meaning_check": "Please review:",
        "m_alt_cleared": "Picture descriptions that said nothing (like “image” or a file name), written anew: {n}.",
        "m_alt_prefix": "Picture descriptions that started with “Image of …”, shortened: {n}.",
        "m_language": "Passages in another language than the document: {n} ({langs}). They got their language, so screen readers switch to the right voice.",
        "m_scope": "Table header cells that now say whether they head a column or a row: {n}.",
        "m_links_made": "Web addresses in the text that were not clickable, made into links: {n}.",
        "m_doc_language": "The language of the document was corrected from “{was}” to “{now}”, because most of the text is in “{now}”.",
        "m_vague_links": "Links that only say something like “click here”: {n} (for example on {pages}). Write link texts that say where the link goes.",
        "m_long_alt": "Picture descriptions longer than {limit} characters: {n} (for example on {pages}). Shorter descriptions are easier to listen to.",
        "m_long_headings": "Very long headings: {n} (for example on {pages}). They may be paragraphs marked as headings.",
        "m_no_headings": "The document has no headings. People who use screen readers cannot jump from section to section.",
        "m_list_like": "Groups of lines that start with bullets or numbers but are not marked as a list: {n} (for example on {pages}).",
        "m_tiny": "Tiny pictures marked as content, probably decoration such as lines or dots: {n}.",
        "m_tables": "Tables without header cells: {n}. Screen readers cannot say which column a value belongs to.",
        "contrast_hidden": "Practically invisible text (for example white text on white): {n}. It was not changed, because it may be hidden on purpose. If it should be read, change its colour in the original file.",
    },
    "de": {
        "title": "Barrierefreiheitsbericht", "file": "Datei", "new_file": "Neue Datei", "result": "Ergebnis",
        "numbers": "In Zahlen", "passes": "Besteht die automatische Prüfung", "yes": "Ja", "no": "Nein",
        "readable": "Text, den assistive Technologien lesen können", "found": "Gefundene Probleme",
        "fixed": "Behobene Probleme", "open": "Noch offene Probleme",
        "to_check": "Texte, die das Werkzeug geschrieben hat und die Sie durchsehen sollten",
        "on_purpose": "Absichtlich nicht behoben", "see_below": " (warum, steht unten)",
        "good_to_know": "Gut zu wissen: Ein Problem wird oft vielfach gezählt, zum Beispiel einmal pro Textzeile. "
                        "Die Zahl der Probleme zeigt also nicht, wie viel Arbeit bleibt. Das Bestehen der "
                        "automatischen Prüfung ist ein gutes Zeichen, aber ein Mensch sollte Lesereihenfolge und "
                        "Texte trotzdem durchsehen.",
        "what_found": "Was gefunden wurde",
        "table_found": "| Problem | Gefunden | Behoben | Noch offen | Was es bedeutet |",
        "what_open": "Was noch offen ist",
        "open_intro": "Diese Probleme müssen von Hand behoben werden, zum Beispiel im Programm, mit dem die PDF "
                      "erstellt wurde.",
        "table_open": "| Problem | Wie oft | Wo | Was Sie tun können |",
        "not_fixed": "Absichtlich nicht behoben",
        "not_fixed_intro": "Das Werkzeug hätte diese Probleme aus der Prüfung verschwinden lassen können, aber nur, "
                           "indem es die Datei für Nutzer von Screenreadern und anderen assistiven Technologien verschlechtert. Deshalb hat es sie nicht "
                           "angefasst. Sie müssen von Hand behoben werden.",
        "table_not_fixed": "| Problem | Wie oft | Warum es nicht behoben wurde |",
        "unknown": "unbekannt", "before_after": "vorher {before}, nachher {after}", "none": "keine",
        "minutes": "etwa {n} Minute{s}", "review_on": "{items} (dauert {time}, siehe Liste unten)",
        "review_off": "{items} (dauert {time}; schalten Sie „Eine Liste zum Durchsehen in den Bericht aufnehmen“ ein, um sie zu sehen)",
        "review_done": "keine mehr: Sie haben sie in der App durchgesehen",
        "yours_title": "Ihre Änderungen",
        "yours_intro": "Sie haben in der App durchgesehen, was das Werkzeug getan hat, und es korrigiert. Die neue PDF enthält Ihre Änderungen.",
        "yours_changed": "{what}: von Ihnen geändert in „{new}“ (das Werkzeug schrieb „{old}“)",
        "yours_reviewed": "{what}: von Ihnen durchgesehen",
        "yours_shown": "Bilder, die Sie mit einer Beschreibung wieder gezeigt haben: {n}",
        "one_title": "Titel", "one_language": "Sprache", "one_images": "Bildbeschreibung",
        "one_formulas": "Formelbeschreibung", "one_links": "Linkbeschreibung", "one_forms": "Beschreibung eines Formularfelds",
        "all_images": "Bildbeschreibungen", "all_formulas": "Formelbeschreibungen", "all_links": "Linkbeschreibungen",
        "all_forms": "Beschreibungen von Formularfeldern",
        "on_page": "{what} auf Seite {page}",
        "new": "{n} neu", "page": "Seite", "pages": "Seiten", "and_more": " und {n} weitere", "whole": "ganzes Dokument",
        "untagged": "Der meiste Text in dieser Datei hat keine Tags. Ohne Tags können assistive Technologien wie Screenreader die Datei nicht "
                    "gut wiedergeben.\n\nWas Sie tun können: Öffnen Sie die Originaldatei in Word. Wählen Sie Datei > "
                    "Speichern unter > PDF > Optionen und schalten Sie „Dokumentstrukturtags für "
                    "Barrierefreiheit“ ein. Speichern Sie die PDF und starten Sie PDFAccessGuru erneut.",
        "no_problems": "Die automatische Prüfung hat keine Probleme gefunden.",
        "all_fixed": "Alle Probleme, die die automatische Prüfung gefunden hat, sind behoben.",
        "some_fixed": "Einige Probleme wurden behoben. Die übrigen stehen unten unter „Was noch offen ist“.",
        "none_fixed": "Das Werkzeug konnte die Probleme in dieser Datei nicht beheben. Sie stehen unten.",
        "ai_title": "Wie die Texte entstanden sind",
        "would_harm": "Die automatische Korrektur würde die Datei für Nutzer assistiver Technologien verschlechtern.",
        "contrast": "Text mit zu wenig Kontrast",
        "contrast_fixed_short": "{n} (behoben: {fixed})",
        "contrast_title": "Farbkontrast",
        "contrast_ok": "Aller messbare Text hat genug Kontrast zu seinem Hintergrund (WCAG 2.2, 1.4.3, Stufe AA).",
        "contrast_off": "Stellen mit zu wenig Kontrast zwischen Text und Hintergrund (WCAG 2.2, 1.4.3, Stufe AA): {n}, auf {pages}. Die Farben wurden nicht geändert, weil die Option „Farbkontrast verbessern“ ausgeschaltet war. Schalten Sie sie ein, wenn sich die Farben dieser Datei ändern dürfen. Bei Vorlagen mit festen Farben wenden Sie sich an die Stelle, die die Vorlage verantwortet.",
        "contrast_fixed": "Stellen mit zu wenig Kontrast, deren Textfarbe gerade so viel dunkler oder heller wurde wie nötig, im gleichen Farbton: {n}. Sonst wurde nichts geändert.",
        "contrast_left": "Stellen, die noch zu wenig Kontrast haben: {n}, auf {pages}. Ihre Textfarbe ließ sich nicht sicher ändern (zum Beispiel braucht weißer Text auf mittlerem Hintergrund einen anderen Hintergrund). Bitte beheben Sie sie in der Originaldatei.",
        "contrast_unclear": "Text auf Bildern oder Farbverläufen, dessen Kontrast sich nicht automatisch messen lässt: {n}. Bitte sehen Sie ihn sich selbst an.",
        "contrast_undone": "Die Farbänderungen wurden rückgängig gemacht, weil sie mehr als nur die Farben verändert hätten.",
        "contrast_example": "Beispiele:",
        "meaning_title": "Bedeutung und Struktur",
        "meaning_intro": "Diese Prüfungen gehen über die automatische PDF/UA-Prüfung hinaus.",
        "meaning_ok": "Es wurden keine Probleme mit Bedeutung oder Struktur gefunden.",
        "meaning_fixed": "Behoben:",
        "meaning_check": "Bitte durchsehen:",
        "m_alt_cleared": "Bildbeschreibungen, die nichts aussagten (etwa „Bild“ oder ein Dateiname), neu geschrieben: {n}.",
        "m_alt_prefix": "Bildbeschreibungen, die mit „Bild von …“ begannen, gekürzt: {n}.",
        "m_language": "Abschnitte in einer anderen Sprache als das Dokument: {n} ({langs}). Sie haben ihre Sprache erhalten, damit Screenreader zur richtigen Stimme wechseln.",
        "m_scope": "Tabellenkopfzellen, die jetzt sagen, ob sie eine Spalte oder eine Zeile überschreiben: {n}.",
        "m_links_made": "Webadressen im Text, die nicht anklickbar waren, als Links angelegt: {n}.",
        "m_doc_language": "Die Sprache des Dokuments wurde von „{was}“ auf „{now}“ korrigiert, weil der meiste Text in „{now}“ ist.",
        "m_vague_links": "Links, die nur etwas wie „hier klicken“ sagen: {n} (zum Beispiel auf {pages}). Schreiben Sie Linktexte, die sagen, wohin der Link führt.",
        "m_long_alt": "Bildbeschreibungen mit mehr als {limit} Zeichen: {n} (zum Beispiel auf {pages}). Kürzere Beschreibungen sind leichter anzuhören.",
        "m_long_headings": "Sehr lange Überschriften: {n} (zum Beispiel auf {pages}). Vielleicht sind es als Überschrift markierte Absätze.",
        "m_no_headings": "Das Dokument hat keine Überschriften. Screenreader-Nutzer können nicht von Abschnitt zu Abschnitt springen.",
        "m_list_like": "Gruppen von Zeilen, die mit Aufzählungszeichen oder Nummern beginnen, aber nicht als Liste markiert sind: {n} (zum Beispiel auf {pages}).",
        "m_tiny": "Winzige Bilder, die als Inhalt markiert sind, vermutlich Dekoration wie Linien oder Punkte: {n}.",
        "m_tables": "Tabellen ohne Kopfzellen: {n}. Screenreader können nicht sagen, zu welcher Spalte ein Wert gehört.",
        "contrast_hidden": "Praktisch unsichtbarer Text (zum Beispiel weißer Text auf Weiß): {n}. Er wurde nicht geändert, weil er absichtlich versteckt sein kann. Wenn er gelesen werden soll, ändern Sie seine Farbe in der Originaldatei.",
    },
}


def _t(language: str, key: str, **values) -> str:
    text = TEXT.get(language, TEXT["en"]).get(key) or TEXT["en"][key]
    return text.format(**values) if values else text


def build_customer_report_markdown(
    report: dict[str, Any],
    include_review_list: bool = False,
    include_pictures: bool = True,
    language: str | None = None,
) -> str:
    """
    Build the customer report.

    include_review_list: add the list of texts the tool wrote itself, for the reader to check.
                         Off by default, because going through it takes time.
    include_pictures:    show a picture of each image or formula in that list (for sighted
                         readers). Without pictures, each entry still shows text to compare with.
    language:            language of the report; by default the language of the fixed PDF
                         (Phase 7b). English and German are built in; other languages are
                         translated by the AI, or the report stays in English and says why.
    """
    metrics = build_report_metrics(report)
    if not language or language == "auto":
        language = _language_of(metrics.output_path)
    wanted, language = language, (language if language in BUILT_IN else "en")
    t = lambda key, **values: _t(language, key, **values)
    review_groups = build_review_groups(report)
    not_fixed_on_purpose = sum((metrics.not_corrected_on_purpose or {}).values())

    lines = [
        f"# {t('title')}",
        "",
        f"{t('file')}: {Path(metrics.input_path).name}",
        "",
        f"{t('new_file')}: {Path(metrics.output_path).name}",
        "",
        f"## {t('result')}",
        "",
        _result_text(metrics, language),
        "",
        f"## {t('numbers')}",
        "",
        f"- {t('passes')}: {t('yes') if metrics.passes_verapdf else t('no')}",
        f"- {t('readable')}: {_text_availability(metrics, language)}",
        f"- {t('found')}: {metrics.detected_count}",
        f"- {t('fixed')}: {metrics.corrected_count}",
        f"- {t('open')}: {metrics.remaining_count}",
        f"- {t('to_check')}: {_review_summary(review_groups, include_review_list, language)}",
        f"- {t('on_purpose')}: {not_fixed_on_purpose}" + (t("see_below") if not_fixed_on_purpose else ""),
        *_contrast_line(metrics.contrast, language),
        "",
        t("good_to_know"),
        "",
        *_user_section(report.get("user_review") or {}, language),
        *_ai_section(report, language),
        f"## {t('what_found')}",
        "",
        t("table_found"),
        "|---|---:|---:|---:|---|",
    ]
    for violation in metrics.violation_metrics:
        lines.append(
            f"| {_format_violation_name(violation, language)} | {violation.detected_count} | {violation.corrected_count} | "
            f"{_remaining_text(violation, language)} | {_escape_table(_customer_explanation(violation, language))} |"
        )

    remaining = [violation for violation in metrics.violation_metrics if violation.remaining_count > 0]
    if remaining:
        contexts_by_name = _remaining_contexts_by_name(report)
        lines.extend(["", f"## {t('what_open')}", "", t("open_intro"), "", t("table_open"), "|---|---:|---|---|"])
        for violation in remaining:
            rule_id = rule_id_of(violation.name)
            lines.append(
                f"| {_format_violation_name(violation, language)} | {violation.remaining_count} | "
                f"{_where(violation.name, contexts_by_name.get(violation.name, []), language)} | "
                f"{_escape_table(problem_todo(rule_id or '', language))} |"
            )

    lines.extend(_meaning_section(metrics.meaning, language))
    lines.extend(_contrast_section(metrics.contrast, language))

    if include_review_list:
        lines.append("")
        lines.extend(review_list_markdown(review_groups, include_pictures=include_pictures, language=language))

    if metrics.not_corrected_on_purpose:
        lines.extend(["", f"## {t('not_fixed')}", "", t("not_fixed_intro"), "", t("table_not_fixed"), "|---|---:|---|"])
        for name, count in metrics.not_corrected_on_purpose.items():
            reason = DISABLED_CORRECTORS.get(name, "")
            why = _reason_sentence(reason) if language == "en" else t("would_harm")
            lines.append(f"| {_escape_table(plain_name(name, language))} | {count} | {_escape_table(why)} |")

    lines.append("")
    markdown = "\n".join(lines)
    if wanted != language:
        markdown, note = translate_markdown(markdown, wanted)
        if note:                                   # right under the title
            title, _, rest = markdown.partition("\n")
            markdown = f"{title}\n\n{note}\n{rest}"
    return markdown


def _user_section(user_review: dict, language: str) -> list[str]:
    """What the user changed or reviewed on the app's review page (Phase 12c); nothing if nothing."""
    changes, reviewed, shown = user_review.get("changes", []), user_review.get("reviewed", []), user_review.get("shown", 0)
    if not (changes or reviewed or shown):
        return []
    t = lambda key, **values: _t(language, key, **values)
    lines = [f"## {t('yours_title')}", "", t("yours_intro"), ""]
    for change in changes:
        what = t("one_" + change.get("group", "images"))
        if change.get("page"):
            what = t("on_page", what=what, page=change["page"])
        lines.append("- " + t("yours_changed", what=what, new=change.get("new", ""), old=change.get("old", "")))
    for group in reviewed:
        lines.append("- " + t("yours_reviewed", what=t("all_" + group)))
    if shown:
        lines.append("- " + t("yours_shown", n=shown))
    return lines + [""]


def _meaning_section(meaning: dict | None, language: str) -> list[str]:
    """Meaning and structure (Phase 10): what was fixed, and what a person should check."""
    if not meaning:
        return []
    t = lambda key, **values: _t(language, key, **values)

    def pages(items) -> str:
        numbers = sorted({page for page, _ in items if page})[:5]
        if not numbers:
            return t("whole")
        return (t("page") if len(numbers) == 1 else t("pages")) + " " + ", ".join(str(n) for n in numbers)

    fixed, check = [], []
    if meaning.get("document_language"):
        was, now = meaning["document_language"]
        fixed.append(t("m_doc_language", was=was, now=now))
    if meaning.get("alt_cleared"):
        fixed.append(t("m_alt_cleared", n=meaning["alt_cleared"]))
    if meaning.get("alt_prefix"):
        fixed.append(t("m_alt_prefix", n=meaning["alt_prefix"]))
    if meaning.get("language_parts"):
        langs = ", ".join(f"{lang}: {n}" for lang, n in (meaning.get("languages") or {}).items())
        fixed.append(t("m_language", n=meaning["language_parts"], langs=langs))
    if meaning.get("table_scope"):
        fixed.append(t("m_scope", n=meaning["table_scope"]))
    if meaning.get("links_made"):
        fixed.append(t("m_links_made", n=meaning["links_made"]))
    if meaning.get("vague_links_count"):
        check.append(t("m_vague_links", n=meaning["vague_links_count"], pages=pages(meaning.get("vague_links", []))))
    if meaning.get("long_alt_count"):
        check.append(t("m_long_alt", n=meaning["long_alt_count"], limit=meaning.get("long_alt_limit", 125),
                          pages=pages(meaning.get("long_alt", []))))
    if meaning.get("long_headings_count"):
        check.append(t("m_long_headings", n=meaning["long_headings_count"], pages=pages(meaning.get("long_headings", []))))
    if meaning.get("no_headings"):
        check.append(t("m_no_headings"))
    if meaning.get("list_like_count"):
        check.append(t("m_list_like", n=meaning["list_like_count"], pages=pages(meaning.get("list_like", []))))
    if meaning.get("tiny_figures"):
        check.append(t("m_tiny", n=meaning["tiny_figures"]))
    if meaning.get("tables_without_headers"):
        check.append(t("m_tables", n=meaning["tables_without_headers"]))
    lines = ["", f"## {t('meaning_title')}", "", t("meaning_intro"), ""]
    if not fixed and not check:
        return lines + [t("meaning_ok")]
    if fixed:
        lines += [t("meaning_fixed"), ""] + [f"- {item}" for item in fixed] + [""]
    if check:
        lines += [t("meaning_check"), ""] + [f"- {item}" for item in check] + [""]
    return lines[:-1]


def _contrast_line(contrast: dict | None, language: str) -> list[str]:
    if not contrast:
        return []
    n = int(contrast.get("low_before", 0))
    value = _t(language, "contrast_fixed_short", n=n, fixed=contrast.get("fixed", 0)) if contrast.get("fixed") else str(n)
    return [f"- {_t(language, 'contrast')}: {value}"]


def _contrast_section(contrast: dict | None, language: str) -> list[str]:
    """Colour contrast (Phase 9): what was measured, what was changed, what is left to do."""
    if not contrast:
        return []
    t = lambda key, **values: _t(language, key, **values)
    left, unclear = int(contrast.get("low_count", 0)), int(contrast.get("unclear", 0))
    pages = contrast.get("pages") or []
    page_text = (t("page") if len(pages) == 1 else t("pages")) + " " + ", ".join(str(p) for p in pages[:_MAX_PAGES_LISTED])
    lines = ["", f"## {t('contrast_title')}", ""]
    if contrast.get("undone"):
        lines += [t("contrast_undone"), ""]
    if contrast.get("fixed"):
        lines += [t("contrast_fixed", n=contrast["fixed"]), ""]
    if left and not contrast.get("switched_on"):
        lines += [t("contrast_off", n=left, pages=page_text), ""]
    elif left:
        lines += [t("contrast_left", n=left, pages=page_text), ""]
    if left:
        examples = contrast.get("low") or []
        if examples:
            lines.append(t("contrast_example"))
            lines += [f"- “{_escape_table(example['text'])}” ({t('page')} {example['page']}, {example['ratio']}:1)"
                      for example in examples[:5]]
            lines.append("")
    if not left and not contrast.get("fixed"):
        lines += [t("contrast_ok"), ""]
    if unclear:
        lines += [t("contrast_unclear", n=unclear), ""]
    if contrast.get("hidden"):
        lines += [t("contrast_hidden", n=contrast["hidden"]), ""]
    return lines[:-1] if lines and lines[-1] == "" else lines


def _language_of(pdf_path: str) -> str:
    return report_language(pdf_path) if pdf_path and Path(pdf_path).is_file() else "en"


def build_customer_report_pdf(
    report: dict[str, Any],
    include_review_list: bool = False,
    include_pictures: bool = True,
    language: str | None = None,
) -> bytes:
    if not language or language == "auto":
        language = _language_of(build_report_metrics(report).output_path)
    markdown = build_customer_report_markdown(report, include_review_list, include_pictures, language)
    title = markdown.split("\n", 1)[0].lstrip("# ").strip()
    return render_report_pdf(
        markdown,
        title,
        images=build_customer_report_images(report) if include_review_list and include_pictures else None,
        language=language,
    )


def build_customer_report_images(report: dict[str, Any]) -> dict[str, bytes]:
    """Pictures used by the review list, keyed by the relative path the Markdown refers to."""
    return review_list_images(build_review_groups(report))


def _reason_sentence(reason: str) -> str:
    """Turn a corrector's reason ('would ...') into a sentence for the reader."""
    if not reason:
        return ""
    if reason.startswith("would "):
        return "The automatic fix " + reason + "."
    return reason[0].upper() + reason[1:] + "."


def _review_summary(groups: list, include_review_list: bool, language: str = "en") -> str:
    if not any(group.items for group in groups):
        return _t(language, "none")
    items = sum(len(group.pending) for group in groups)
    if not items:
        return _t(language, "review_done")
    minutes = estimated_minutes(groups)
    plural = ("" if minutes == 1 else "s") if language == "en" else ("" if minutes == 1 else "n")
    time_text = _t(language, "minutes", n=minutes, s=plural)
    return _t(language, "review_on" if include_review_list else "review_off", items=items, time=time_text)


def _remaining_text(violation: ViolationMetric, language: str = "en") -> str:
    if violation.new_count:
        return f"{violation.remaining_count} ({_t(language, 'new', n=violation.new_count)})"
    return str(violation.remaining_count)


def _text_availability(metrics: ReportMetrics, language: str = "en") -> str:
    """Share of text that screen readers can reach, before and after."""
    def share(tagging: dict | None) -> str:
        if not tagging or not tagging.get("total"):
            return _t(language, "unknown")
        return f"{tagging['tagged_share'] * 100:.0f}%"
    return _t(language, "before_after", before=share(metrics.text_tagging_input), after=share(metrics.text_tagging_output))


def _result_text(metrics: ReportMetrics, language: str = "en") -> str:
    output = metrics.text_tagging_output or {}
    if output.get("total") and output.get("tagged_share", 0) < 0.5:
        return _t(language, "untagged")
    if metrics.detected_count == 0:
        return _t(language, "no_problems")
    if metrics.remaining_count == 0:
        return _t(language, "all_fixed")
    if metrics.corrected_count > 0:
        return _t(language, "some_fixed")
    return _t(language, "none_fixed")


def _customer_explanation(violation: ViolationMetric, language: str = "en") -> str:
    rule_id = rule_id_of(violation.name)
    meaning = problem_meaning(rule_id, language) if rule_id else ""
    if meaning:
        return meaning
    entry = violation.taxonomy_entry
    if entry is None:
        return ""
    return entry.german_explanation or entry.description


def _format_violation_name(violation: ViolationMetric, language: str = "en") -> str:
    """The plain name of the problem (the technical name and links are in the technical report)."""
    return _escape_table(plain_name(violation.name, language))


def _remaining_contexts_by_name(report: dict[str, Any]) -> dict[str, list[str]]:
    for phase in reversed(report.get("phases", [])):
        if phase.get("name") != "verification":
            continue
        summary = phase.get("summary", {})
        return {
            str(name): [str(context) for context in contexts]
            for name, contexts in summary.get("contexts_by_name", {}).items()
        }
    return {}


def _where(violation_name: str, contexts: list[str], language: str = "en") -> str:
    """Pages on which a problem remains, in a short form ('pages 1, 2, 5 and 9 more')."""
    pages = sorted({int(m.group(1)) + 1 for c in contexts if (m := re.search(r"(?:^|/)pages\[(\d+)\]", c))})
    if pages:
        shown = ", ".join(str(page) for page in pages[:_MAX_PAGES_LISTED])
        more = _t(language, "and_more", n=len(pages) - _MAX_PAGES_LISTED) if len(pages) > _MAX_PAGES_LISTED else ""
        return _t(language, "page" if len(pages) == 1 else "pages") + " " + shown + more
    return _t(language, "whole")


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _all_messages(report: dict[str, Any]) -> list[str]:
    """Every message in the report, also those recorded inside single corrections."""
    found: list[str] = []

    def walk(value) -> None:
        if isinstance(value, dict):
            message = value.get("message")
            if isinstance(message, str):
                found.append(message)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(report.get("phases", []))
    return found


def _ai_section(report: dict[str, Any], language: str = "en") -> list[str]:
    """How texts like picture descriptions were written: by which AI, or with simple rules."""
    from pdfaccessguru.LLM.fallback import translate_note

    messages = _all_messages(report)
    status = next((m for m in messages if m.startswith("Texts such as picture descriptions are written by")
                   or m.startswith("No AI model is used")), None)
    notes = list(dict.fromkeys(m[len("Without AI: "):] for m in messages if m.startswith("Without AI: ")))
    if status is None and not notes:
        return []
    if language == "de":
        status = translate_note(status) if status else status
        notes = [translate_note(note) for note in notes]
    lines = [f"## {_t(language, 'ai_title')}", ""]
    if status:
        lines += [status, ""]
    lines += [f"- {note}" for note in notes]
    return lines + ([""] if notes else [])
