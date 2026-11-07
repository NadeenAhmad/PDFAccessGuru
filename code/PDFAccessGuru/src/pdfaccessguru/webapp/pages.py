"""
The pages of the browser app, in English and German (Phase 7a).

Accessibility rules followed on every page: one h1 per page and a heading order without gaps;
every field has a visible label, help texts are connected with aria-describedby; options are
grouped in fieldsets with a legend; everything works with the keyboard and has a clearly visible
focus; progress is announced in a polite live region and errors in an alert; colours have a
contrast of at least 7:1 (light and dark mode); no time limits; nothing moves on its own.
"""

from __future__ import annotations

import html

TEXT = {
    "en": {
        "title": "PDFAccessGuru",
        "skip": "Skip to the main content",
        "home_label": "PDFAccessGuru, start page",
        "lang_nav": "Language",
        "hidden_title": "Hidden as decoration",
        "hidden_intro": "The tool hid these from screen readers and other assistive technologies, because they look "
                        "like decoration. If a picture carries meaning, tick it and describe it.",
        "hidden_none": "Nothing on these pages was hidden as decoration, except lines and shapes.",
        "hidden_show": "Show this picture to assistive technologies (it carries meaning)",
        "hidden_where": "On page {pages}",
        "hidden_describe": "Description of this picture",
        "hidden_text": "Text hidden as page header, footer or page number",
        "hidden_pages": "on {n} page(s)",
        "empty_picture": "Please describe every picture you want to show. Nothing was saved.",
        "cannot_show": "The picture could not be shown in this file. Nothing was saved.",
        "summary_label": "Result",
        "badge_ok": "Passes the automatic check",
        "badge_warn": "Some problems are still open",
        "n_fixed": "Problems fixed",
        "n_open": "Still open",
        "n_check": "Texts to check",
        "next_steps": "Next steps",
        "download_pdf_short": "The accessible PDF",
        "report_pdf_note": "The report as an accessible PDF",
        "report_md_note": "The report as plain text, for editing or sharing",
        "check_note": "Picture descriptions, link texts, title, language, and what was hidden as decoration",
        "preview_note": "The new PDF as assistive technologies present it: in reading order, with headings and picture descriptions",
        "footer": "PDFAccessGuru {version}. Runs only on this computer. Free and open source.",
        "hero_title": "Make PDF files accessible",
        "promise_local": "Your files stay on this computer, unless you choose an online AI service",
        "promise_standard": "Checked against PDF/UA, the standard for accessible PDF",
        "promise_original": "The original is never changed",
        "promise_free": "Free and open source",
        "intro": "Makes PDF files accessible to everyone, including people with disabilities. PDFAccessGuru adds "
                 "what assistive technologies such as screen readers, screen magnifiers and read-aloud tools need: "
                 "headings, lists and tables, a reading order, descriptions of pictures, and the language.",
        "file_legend": "1. Choose PDF files",
        "file_label": "One or more PDF files",
        "file_help": "The original files are not changed. You get a new, improved copy of each. To choose several files, hold Ctrl (on a Mac: Cmd) while you click.",
        "ai_legend": "2. Who writes texts like picture descriptions?",
        "ai_auto": "Automatic (recommended): an online AI if you have set up a key for one, otherwise an AI on this computer (Ollama), otherwise simple rules",
        "ai_ollama": "An AI that runs only on this computer (Ollama: free and private; it must be installed)",
        "ai_cloud": ("An online AI like ChatGPT (from OpenAI), or Claude, Gemini and others (through OpenRouter). Pictures "
                    "and text from your file are sent over the internet to that company. You need an account key from them."),
        "ai_none": "No AI: simple rules only (fast, but the texts are less helpful)",
        "ai_status": "Right now: {status}.",
        "local_label": "Never send anything from my file to the internet",
        "local_help": "Use this for confidential files. Then only an AI on this computer (Ollama), or simple rules, are used.",
        "contrast_legend": "3. Colours",
        "contrast_label": "Improve colour contrast (changes text colours)",
        "contrast_help": "Makes text that is hard to read a little darker or lighter, just enough. Leave this off for "
                         "templates whose colours must not change, for example official templates. Text with too "
                         "little contrast is listed in the report either way.",
        "report_legend": "4. Report",
        "report_language": "Each report is written in the language of its PDF.",
        "writing_report": "Writing the report",
        "n_files": "{n} files",
        "file_n_of": "File {n} of {total} ({name})",
        "download_zip": "All new files and reports in one ZIP file",
        "summary": "Passes the automatic check: {passes}. Problems fixed: {fixed}. Still open: {open}.",
        "yes": "yes", "no": "no",
        "show_report": "Show the report",
        "not_done": "Not processed, because the work was stopped.",
        "review_label": "Add a list of everything the tool decided by itself, to check it",
        "review_help": "For example picture descriptions, the title, the language and the headings. Takes a few "
                       "minutes. Every entry can be checked without seeing the page.",
        "pictures_label": "Show the pictures in that list",
        "pictures_help": "For sighted readers. Without pictures, every entry still has a text to compare with.",
        "protected_legend": "5. Only for protected PDFs (optional)",
        "password_label": "Owner password of the PDF",
        "password_help": "Only needed if the file is protected and blocks screen readers and other assistive "
                         "technologies. The password is used "
                         "once and not stored.",
        "start": "Make the PDF accessible",
        "busy": "Another file is being worked on. Please wait until it is finished.",
        "working_title": "Working on {name}",
        "working_help": "This can take a few minutes for long files. You can leave this page open; it updates by itself.",
        "progress_label": "Progress",
        "cancel": "Stop",
        "done_title": "Done: {name}",
        "downloads": "Downloads",
        "download_pdf": "The accessible PDF ({name}, {size})",
        "download_report_pdf": "Report (PDF)",
        "download_report_md": "Report (Markdown text)",
        "report": "Report",
        "again": "Check another file",
        "error_title": "Something went wrong",
        "error_help": "The file could not be processed. The message below says why.",
        "stopped": "Stopped. Nothing was saved.",
        "no_file": "Please choose a PDF file.",
        "not_pdf": "These files are not PDFs: {names}. Please choose PDF files only.",
        "quit": "Close the app",
        "quit_done": "The app is closed. You can close this browser tab.",
        "update": "A new version of PDFAccessGuru is available: {version}.",
        "update_button": "Update now",
        "update_help": "PDFAccessGuru closes, installs the new version and opens again. This takes about a minute.",
        "updating": "PDFAccessGuru is being updated and opens again in about a minute. You can close this tab.",
        "update_manual": "The update could not be started automatically. Run this in a terminal: pdfaccessguru update",
        "tools_needed": "Before the first use, PDFAccessGuru needs two free helper programs and some free fonts "
                        "(Java, veraPDF and the Liberation fonts, about 77 MB). They are downloaded once into "
                        "your user folder. No admin rights are needed.",
        "tools_button": "Download them now",
        "tools_working": "Downloading the helper programs: {text}",
        "tools_failed": "The helper programs could not be downloaded: {error}",
        "tools_done": "The helper programs are ready.",
        "check_link": "Check and correct the tool's choices",
        "preview_link": "Show the reading order",
        "check_title": "Check the tool's choices: {name}",
        "check_intro": "The tool wrote these texts and made these choices by itself. Correct anything that is wrong, then save. Your changes go "
                       "straight into the new PDF. To check a text, compare it with the text under its name "
                       "(the caption, the text nearby, or where a link goes).",
        "checked": "checked",
        "group_document": "Title and language of the document",
        "group_pictures": "Picture descriptions ({n})",
        "group_formulas": "Formula descriptions ({n})",
        "group_links": "Link descriptions ({n})",
        "group_fields": "Form field descriptions ({n})",
        "label_title": "Title of the document",
        "label_lang": "Language of the document",
        "lang_help": "A short code: en for English, de for German, ar for Arabic, or with a country, like en-GB.",
        "label_pictures": "Picture on page {page}",
        "label_formulas": "Formula on page {page}",
        "label_links": "Link on page {page}",
        "label_fields": "Form field on page {page}",
        "accept_pictures": "Save, and mark all picture descriptions as checked",
        "accept_formulas": "Save, and mark all formula descriptions as checked",
        "accept_links": "Save, and mark all link descriptions as checked",
        "accept_fields": "Save, and mark all form field descriptions as checked",
        "nothing_written": "The tool did not write any other texts for this file.",
        "save": "Save my changes",
        "report_stays": "The report still shows the texts as the tool wrote them.",
        "back": "Back to the results",
        "changed_meanwhile": "The file was changed in the meantime, for example in another tab. Nothing was saved. Please check the texts again.",
        "empty_text": "A text cannot be empty. Nothing was saved.",
        "bad_language": "The language must be a short code like en, de or en-GB. Nothing was saved.",
        "saved": "Saved. Texts changed: {n}.",
        "preview_title": "Reading order: {name}",
        "preview_intro": "This is the new PDF as screen readers and read-aloud tools present it, in this order. Decoration is left out. Check "
                         "that the order and the headings make sense. Pictures are shown by their description.",
    },
    "de": {
        "title": "PDFAccessGuru",
        "skip": "Zum Hauptinhalt springen",
        "home_label": "PDFAccessGuru, Startseite",
        "lang_nav": "Sprache",
        "hidden_title": "Als Dekoration ausgeblendet",
        "hidden_intro": "Das Werkzeug hat diese Dinge vor Screenreadern und anderen assistiven Technologien "
                        "ausgeblendet, weil sie wie Dekoration aussehen. Wenn ein Bild etwas aussagt, kreuzen Sie es an "
                        "und beschreiben Sie es.",
        "hidden_none": "Auf diesen Seiten wurde außer Linien und Formen nichts als Dekoration ausgeblendet.",
        "hidden_show": "Dieses Bild für assistive Technologien zeigen (es sagt etwas aus)",
        "hidden_where": "Auf Seite {pages}",
        "hidden_describe": "Beschreibung dieses Bildes",
        "hidden_text": "Als Kopfzeile, Fußzeile oder Seitenzahl ausgeblendeter Text",
        "hidden_pages": "auf {n} Seite(n)",
        "empty_picture": "Bitte beschreiben Sie jedes Bild, das gezeigt werden soll. Es wurde nichts gespeichert.",
        "cannot_show": "Das Bild ließ sich in dieser Datei nicht zeigen. Es wurde nichts gespeichert.",
        "summary_label": "Ergebnis",
        "badge_ok": "Besteht die automatische Prüfung",
        "badge_warn": "Einige Probleme sind noch offen",
        "n_fixed": "Behobene Probleme",
        "n_open": "Noch offen",
        "n_check": "Zu prüfende Texte",
        "next_steps": "Nächste Schritte",
        "download_pdf_short": "Die barrierefreie PDF",
        "report_pdf_note": "Der Bericht als barrierefreie PDF",
        "report_md_note": "Der Bericht als reiner Text, zum Bearbeiten oder Weitergeben",
        "check_note": "Bildbeschreibungen, Linktexte, Titel, Sprache und was als Dekoration ausgeblendet wurde",
        "preview_note": "Die neue PDF so, wie assistive Technologien sie wiedergeben: in Lesereihenfolge, mit Überschriften und Bildbeschreibungen",
        "footer": "PDFAccessGuru {version}. Läuft nur auf diesem Computer. Kostenlos und quelloffen.",
        "hero_title": "PDF-Dateien barrierefrei machen",
        "promise_local": "Ihre Dateien bleiben auf diesem Computer, außer Sie wählen einen Online-KI-Dienst",
        "promise_standard": "Geprüft nach PDF/UA, dem Standard für barrierefreie PDF",
        "promise_original": "Das Original wird nie verändert",
        "promise_free": "Kostenlos und quelloffen",
        "intro": "Macht PDF-Dateien barrierefrei: für alle nutzbar, auch für Menschen mit Behinderungen. "
                 "PDFAccessGuru ergänzt, was assistive Technologien wie Screenreader, Vergrößerungssoftware und "
                 "Vorlesefunktionen brauchen: Überschriften, Listen und Tabellen, eine Lesereihenfolge, "
                 "Bildbeschreibungen und die Sprache.",
        "file_legend": "1. PDF-Dateien wählen",
        "file_label": "Eine oder mehrere PDF-Dateien",
        "file_help": "Die Originaldateien werden nicht verändert. Sie erhalten von jeder eine neue, verbesserte Kopie. Für mehrere Dateien halten Sie beim Klicken Strg gedrückt (auf dem Mac: Cmd).",
        "ai_legend": "2. Wer schreibt Texte wie Bildbeschreibungen?",
        "ai_auto": "Automatisch (empfohlen): eine Online-KI, falls Sie einen Schlüssel dafür eingerichtet haben, sonst eine KI auf diesem Computer (Ollama), sonst einfache Regeln",
        "ai_ollama": "Eine KI, die nur auf diesem Computer läuft (Ollama: kostenlos und privat; muss installiert sein)",
        "ai_cloud": ("Eine Online-KI wie ChatGPT (von OpenAI) oder Claude, Gemini und andere (über OpenRouter). Bilder und "
                    "Text aus Ihrer Datei werden über das Internet an diese Firma gesendet. Sie brauchen einen Zugangsschlüssel von ihr."),
        "ai_none": "Keine KI: nur einfache Regeln (schnell, aber die Texte sind weniger hilfreich)",
        "ai_status": "Derzeit: {status}.",
        "local_label": "Nichts aus meiner Datei ins Internet senden",
        "local_help": "Für vertrauliche Dateien. Dann wird nur eine KI auf diesem Computer (Ollama) oder einfache Regeln verwendet.",
        "contrast_legend": "3. Farben",
        "contrast_label": "Farbkontrast verbessern (ändert Textfarben)",
        "contrast_help": "Macht schwer lesbaren Text etwas dunkler oder heller, gerade so viel wie nötig. Lassen Sie "
                         "dies aus bei Vorlagen, deren Farben sich nicht ändern dürfen, zum Beispiel amtlichen "
                         "Vorlagen. Text mit zu wenig Kontrast steht so oder so im Bericht.",
        "report_legend": "4. Bericht",
        "report_language": "Jeder Bericht wird in der Sprache seiner PDF geschrieben.",
        "writing_report": "Der Bericht wird geschrieben",
        "n_files": "{n} Dateien",
        "file_n_of": "Datei {n} von {total} ({name})",
        "download_zip": "Alle neuen Dateien und Berichte in einer ZIP-Datei",
        "summary": "Besteht die automatische Prüfung: {passes}. Behobene Probleme: {fixed}. Noch offen: {open}.",
        "yes": "ja", "no": "nein",
        "show_report": "Bericht zeigen",
        "not_done": "Nicht bearbeitet, weil die Arbeit abgebrochen wurde.",
        "review_label": "Eine Liste von allem hinzufügen, was das Werkzeug selbst entschieden hat, um es zu prüfen",
        "review_help": "Zum Beispiel Bildbeschreibungen, Titel, Sprache und Überschriften. Das Durchgehen dauert einige "
                       "Minuten. Jeder Eintrag lässt sich prüfen, ohne die Seite zu sehen.",
        "pictures_label": "Bilder in dieser Liste zeigen",
        "pictures_help": "Für sehende Leser. Ohne Bilder hat jeder Eintrag trotzdem einen Vergleichstext.",
        "protected_legend": "5. Nur für geschützte PDFs (optional)",
        "password_label": "Besitzerkennwort der PDF",
        "password_help": "Nur nötig, wenn die Datei geschützt ist und Screenreader und andere assistive Technologien "
                         "sperrt. Das Kennwort wird einmal "
                         "verwendet und nicht gespeichert.",
        "start": "PDF barrierefrei machen",
        "busy": "Gerade wird eine andere Datei bearbeitet. Bitte warten Sie, bis sie fertig ist.",
        "working_title": "{name} wird bearbeitet",
        "working_help": "Bei langen Dateien kann das einige Minuten dauern. Lassen Sie diese Seite offen; sie aktualisiert sich selbst.",
        "progress_label": "Fortschritt",
        "cancel": "Abbrechen",
        "done_title": "Fertig: {name}",
        "downloads": "Herunterladen",
        "download_pdf": "Die barrierefreie PDF ({name}, {size})",
        "download_report_pdf": "Bericht (PDF)",
        "download_report_md": "Bericht (Markdown-Text)",
        "report": "Bericht",
        "again": "Weitere Datei prüfen",
        "error_title": "Etwas ist schiefgegangen",
        "error_help": "Die Datei konnte nicht bearbeitet werden. Die Meldung unten sagt, warum.",
        "stopped": "Abgebrochen. Es wurde nichts gespeichert.",
        "no_file": "Bitte wählen Sie eine PDF-Datei.",
        "not_pdf": "Diese Dateien sind keine PDFs: {names}. Bitte wählen Sie nur PDF-Dateien.",
        "quit": "App schließen",
        "quit_done": "Die App ist geschlossen. Sie können diesen Browser-Tab schließen.",
        "update": "Eine neue Version von PDFAccessGuru ist verfügbar: {version}.",
        "update_button": "Jetzt aktualisieren",
        "update_help": "PDFAccessGuru schließt sich, installiert die neue Version und öffnet sich wieder. Das dauert etwa eine Minute.",
        "updating": "PDFAccessGuru wird aktualisiert und öffnet sich in etwa einer Minute wieder. Sie können diesen Tab schließen.",
        "update_manual": "Die Aktualisierung ließ sich nicht automatisch starten. Geben Sie im Terminal ein: pdfaccessguru update",
        "tools_needed": "Vor der ersten Verwendung braucht PDFAccessGuru zwei kostenlose Hilfsprogramme und einige "
                        "kostenlose Schriften (Java, veraPDF und die Liberation-Schriften, etwa 77 MB). Sie werden "
                        "einmal in Ihren Benutzerordner geladen. Es sind keine Administratorrechte nötig.",
        "tools_button": "Jetzt herunterladen",
        "tools_working": "Die Hilfsprogramme werden geladen: {text}",
        "tools_failed": "Die Hilfsprogramme konnten nicht geladen werden: {error}",
        "tools_done": "Die Hilfsprogramme sind bereit.",
        "check_link": "Die Entscheidungen des Werkzeugs prüfen und korrigieren",
        "preview_link": "Lesereihenfolge zeigen",
        "check_title": "Entscheidungen prüfen: {name}",
        "check_intro": "Diese Texte und Entscheidungen stammen vom Werkzeug selbst. Korrigieren Sie, was nicht stimmt, und "
                       "speichern Sie. Ihre Änderungen kommen direkt in die neue PDF. Zum Prüfen vergleichen Sie den "
                       "Text mit dem Text unter seinem Namen (Bildunterschrift, Text in der Nähe oder Linkziel).",
        "checked": "geprüft",
        "group_document": "Titel und Sprache des Dokuments",
        "group_pictures": "Bildbeschreibungen ({n})",
        "group_formulas": "Formelbeschreibungen ({n})",
        "group_links": "Linkbeschreibungen ({n})",
        "group_fields": "Beschreibungen von Formularfeldern ({n})",
        "label_title": "Titel des Dokuments",
        "label_lang": "Sprache des Dokuments",
        "lang_help": "Ein kurzer Code: de für Deutsch, en für Englisch, ar für Arabisch, oder mit Land, z. B. de-AT.",
        "label_pictures": "Bild auf Seite {page}",
        "label_formulas": "Formel auf Seite {page}",
        "label_links": "Link auf Seite {page}",
        "label_fields": "Formularfeld auf Seite {page}",
        "accept_pictures": "Speichern und alle Bildbeschreibungen als geprüft markieren",
        "accept_formulas": "Speichern und alle Formelbeschreibungen als geprüft markieren",
        "accept_links": "Speichern und alle Linkbeschreibungen als geprüft markieren",
        "accept_fields": "Speichern und alle Beschreibungen von Formularfeldern als geprüft markieren",
        "nothing_written": "Das Werkzeug hat für diese Datei keine weiteren Texte geschrieben.",
        "save": "Meine Änderungen speichern",
        "report_stays": "Der Bericht zeigt weiterhin die Texte, wie das Werkzeug sie geschrieben hat.",
        "back": "Zurück zu den Ergebnissen",
        "changed_meanwhile": "Die Datei wurde inzwischen geändert, zum Beispiel in einem anderen Tab. Es wurde nichts gespeichert. Bitte prüfen Sie die Texte erneut.",
        "empty_text": "Ein Text darf nicht leer sein. Es wurde nichts gespeichert.",
        "bad_language": "Die Sprache muss ein kurzer Code sein, z. B. de, en oder de-AT. Es wurde nichts gespeichert.",
        "saved": "Gespeichert. Geänderte Texte: {n}.",
        "preview_title": "Lesereihenfolge: {name}",
        "preview_intro": "So geben Screenreader und Vorlesefunktionen die neue PDF wieder, in dieser Reihenfolge. Dekoration wird ausgelassen. "
                         "Prüfen Sie, ob Reihenfolge und Überschriften Sinn ergeben. Bilder erscheinen als ihre Beschreibung.",
    },
}

# Atkinson Hyperlegible, made by the Braille Institute for readers with low vision (SIL Open
# Font License, see static/OFL-Atkinson-Hyperlegible.txt); bundled, so nothing is loaded from the internet.
FONT_FACES = """@font-face { font-family: 'Atkinson Hyperlegible'; font-style: normal; font-weight: 400; font-display: swap; src: url('{static}atkinson-hyperlegible-400-latin-ext.woff2') format('woff2'); unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF; }
@font-face { font-family: 'Atkinson Hyperlegible'; font-style: normal; font-weight: 400; font-display: swap; src: url('{static}atkinson-hyperlegible-400-latin.woff2') format('woff2'); unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; }
@font-face { font-family: 'Atkinson Hyperlegible'; font-style: normal; font-weight: 700; font-display: swap; src: url('{static}atkinson-hyperlegible-700-latin-ext.woff2') format('woff2'); unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF; }
@font-face { font-family: 'Atkinson Hyperlegible'; font-style: normal; font-weight: 700; font-display: swap; src: url('{static}atkinson-hyperlegible-700-latin.woff2') format('woff2'); unicode-range: U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD; }"""

# Colours: the logo's navy and teal on the warm "paper" of the students' first window. Every
# text colour has a contrast of at least 7:1 on its background (checked in the tests), in light
# and in dark mode; borders of fields and the focus ring at least 3:1.
CSS = """
:root { --paper: #f6f2ea; --card: #ffffff; --ink: #17202b; --muted: #3d4550; --navy: #0b2a5b;
        --teal: #00594f; --on-teal: #ffffff; --link: #00594f; --line: #6b6458; --soft: #ddd5c6;
        --focus: #b35300; --error: #9e1220; --ok-bg: #e2f1ec; --ok-ink: #00423a; --warn-bg: #fbeed6;
        --warn-ink: #5c3200; --logo-ink: #0b2a5b; --logo-teal: #00796b; --logo-paper: #ffffff; --logo-check: #ffffff;
        --shadow: 0 1px 2px rgba(23, 32, 43, .06), 0 6px 20px rgba(23, 32, 43, .06); }
@media (prefers-color-scheme: dark) {
  :root { --paper: #0e1622; --card: #162131; --ink: #eef2f7; --muted: #c6cfda; --navy: #dbe6f7;
          --teal: #7fdccb; --on-teal: #06231f; --link: #8fe3d4; --line: #95a2b3; --soft: #2a3a52;
          --focus: #ffb35c; --error: #ffa3a3; --ok-bg: #123530; --ok-ink: #b5f2e6; --warn-bg: #3a2a10;
          --warn-ink: #ffd894; --logo-ink: #eef2f7; --logo-teal: #7fdccb; --logo-paper: #162131; --logo-check: #06231f;
          --shadow: none; }
}
* { box-sizing: border-box; }
html { background: var(--paper); }
body { margin: 0; background: var(--paper); color: var(--ink);
       font: 1.125rem/1.6 "Atkinson Hyperlegible", system-ui, -apple-system, "Segoe UI", sans-serif; }
.top { background: var(--card); border-bottom: 1px solid var(--soft); }
.top .bar, main, footer { max-width: 54rem; margin: 0 auto; padding: 0 1.25rem; }
.top .bar { display: flex; align-items: center; justify-content: space-between; gap: 1rem; min-height: 4.5rem; flex-wrap: wrap; }
.brand { display: inline-flex; align-items: center; padding: .5rem 0; }
.brand svg { height: 2.6rem; width: auto; display: block; }
.logo .ink { fill: var(--logo-ink); } .logo .teal { fill: var(--logo-teal); }
.logo .page { fill: var(--logo-paper); stroke: var(--logo-ink); } .logo .check { fill: var(--logo-check); }
.top nav a { font-weight: 700; }
main { padding-top: 1.75rem; padding-bottom: 2rem; }
footer { color: var(--muted); font-size: 1rem; padding-bottom: 2rem; }
a { color: var(--link); text-underline-offset: .18em; }
a:hover { text-decoration-thickness: 2px; }
:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; border-radius: .2rem; }
.skip { position: absolute; left: -999px; }
.skip:focus { left: 1rem; top: 1rem; background: var(--card); padding: .6rem 1rem; z-index: 10; }
h1 { font-size: 2.1rem; line-height: 1.2; margin: .2rem 0 .6rem; color: var(--navy); }
h2 { font-size: 1.45rem; line-height: 1.3; color: var(--navy); margin: 1.4rem 0 .6rem; }
h3 { font-size: 1.2rem; color: var(--navy); }
.lead { font-size: 1.25rem; max-width: 42rem; margin: 0 0 .8rem; }
.promises { list-style: none; padding: 0; margin: 0 0 1.5rem; display: flex; flex-wrap: wrap; gap: .5rem 1.4rem; }
.promises li::before { content: "✓"; color: var(--teal); font-weight: 700; margin-right: .45rem; }
.card { background: var(--card); border: 1px solid var(--soft); border-radius: 1rem; box-shadow: var(--shadow);
        padding: 1.25rem 1.4rem; margin: 0 0 1.25rem; }
fieldset.card { min-width: 0; }
.card > :first-child, .card > h2:first-child { margin-top: 0; }
legend { float: left; width: 100%; padding: 0; margin: 0 0 .8rem; font-size: 1.3rem; font-weight: 700; color: var(--navy);
         display: flex; align-items: center; gap: .7rem; }
legend + * { clear: both; }
legend h2 { font: inherit; color: inherit; margin: 0; display: flex; align-items: center; gap: .7rem; }
.num { display: inline-flex; align-items: center; justify-content: center; flex: none; width: 2.1rem; height: 2.1rem;
       border-radius: 50%; background: var(--teal); color: var(--on-teal); font-size: 1.1rem; }
label { font-weight: 700; }
.help { color: var(--muted); margin: .15rem 0 .7rem; font-size: 1.02rem; }
.drop { border: 2px dashed var(--line); border-radius: .8rem; padding: 1rem; background: var(--paper); }
.drop:has(input:focus-visible) { outline: 3px solid var(--focus); outline-offset: 3px; }
input[type=file] { width: 100%; font: inherit; font-size: 1.05rem; padding: 1.2rem .5rem; color: var(--ink); cursor: pointer; }
input[type=file]:focus-visible { outline: none; }
input[type=file]::file-selector-button { font: inherit; font-weight: 700; margin-right: 1rem; padding: .6rem 1.1rem;
       border-radius: .5rem; border: 2px solid var(--teal); background: var(--card); color: var(--link); cursor: pointer; }
.choice { display: flex; gap: .75rem; align-items: flex-start; margin: .5rem 0; padding: .7rem .9rem;
          border: 2px solid var(--soft); border-radius: .7rem; }
.choice:has(input:checked) { border-color: var(--teal); background: var(--ok-bg); }
.choice input { width: 1.35rem; height: 1.35rem; margin-top: .2rem; flex: none; accent-color: var(--teal); }
.choice label { font-weight: 600; }
.choices-help { margin-top: -.2rem; }
input[type=password], input[type=text], textarea, select {
       width: 100%; font: inherit; font-size: 1.05rem; padding: .6rem .7rem; border: 2px solid var(--line);
       border-radius: .5rem; background: var(--card); color: var(--ink); }
input[type=password] { max-width: 24rem; }
button, .button { display: inline-flex; align-items: center; gap: .5rem; font: inherit; font-weight: 700; font-size: 1.1rem;
       padding: .8rem 1.5rem; border-radius: .7rem; border: 2px solid var(--teal); background: var(--teal);
       color: var(--on-teal); cursor: pointer; text-decoration: none; }
button.big { font-size: 1.25rem; padding: 1rem 2rem; }
button.secondary, .button.secondary { background: var(--card); color: var(--link); }
button:disabled { opacity: .55; cursor: not-allowed; }
.actions { display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; margin: 1.5rem 0; }
.status { background: var(--ok-bg); color: var(--ok-ink); padding: .9rem 1.1rem; border-radius: .7rem; margin: 0 0 1.25rem; }
.alert { background: var(--card); border: 2px solid var(--error); color: var(--error); padding: .9rem 1.1rem;
         border-radius: .7rem; margin: 0 0 1.25rem; font-weight: 700; }
progress { width: 100%; height: 1.5rem; accent-color: var(--teal); }
.badge { display: inline-flex; align-items: center; gap: .55rem; font-weight: 700; font-size: 1.15rem;
         padding: .45rem 1rem; border-radius: 2rem; margin: 0 0 1rem; }
.badge.ok { background: var(--ok-bg); color: var(--ok-ink); }
.badge.warn { background: var(--warn-bg); color: var(--warn-ink); }
.badge .mark { font-size: 1.2rem; }
.numbers { display: grid; grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr)); gap: 1rem; margin: 0; }
.numbers div { border: 1px solid var(--soft); border-radius: .8rem; padding: .8rem 1rem; }
.numbers dt { color: var(--muted); font-size: 1rem; }
.numbers dd { margin: 0; font-size: 2.2rem; font-weight: 700; color: var(--navy); line-height: 1.2; }
.links { list-style: none; padding: 0; margin: 0; display: grid; gap: .7rem; }
.links a { display: block; padding: .8rem 1rem; border: 2px solid var(--soft); border-radius: .7rem; font-weight: 700;
           text-decoration: none; }
.links a:hover { border-color: var(--teal); }
.links .note { display: block; font-weight: 400; color: var(--muted); font-size: 1rem; }
summary { cursor: pointer; font-weight: 700; padding: .4rem 0; color: var(--link); }
details { margin: .5rem 0 0; }
.entry { margin: 0 0 1.4rem; }
.entry label { display: block; }
.entry img { display: block; max-width: 100%; max-height: 260px; margin: .4rem 0; border: 1px solid var(--soft); border-radius: .4rem; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { border: 1px solid var(--soft); padding: .45rem .65rem; text-align: start; vertical-align: top; }
thead th { background: var(--paper); }
.report h2 { margin-top: 1.6rem; }
.preview .page-marker { color: var(--muted); border-top: 1px solid var(--soft); padding-top: .3rem; font-size: 1rem; margin-top: 1.4rem; }
.preview .missing { color: var(--error); font-weight: 700; }
.preview ul { list-style: none; padding-left: 1.2rem; }      /* the PDF's own bullet or number is in the text */
textarea { field-sizing: content; min-height: 3.4em; }
@media (max-width: 40rem) { h1 { font-size: 1.7rem; } .card { padding: 1rem; } button.big { width: 100%; justify-content: center; } }
@media (forced-colors: active) { .num, .badge, .choice, .card { border: 1px solid CanvasText; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
"""


def _logo() -> str:
    """The logo (from static/logo.svg) inline, coloured by the page theme, hidden from screen readers
    (the link around it has the name)."""
    from pathlib import Path
    import re

    svg = (Path(__file__).with_name("static") / "logo.svg").read_text(encoding="utf-8")
    svg = re.sub(r"<title[^>]*>.*?</title>|<desc[^>]*>.*?</desc>", "", svg, flags=re.S)
    svg = svg.replace('role="img" aria-labelledby="pag-lockup-title" aria-describedby="pag-lockup-desc"',
                      'class="logo" aria-hidden="true" focusable="false"')
    svg = svg.replace('fill="#FFFFFF" stroke="#0B2A5B"', 'class="page"')
    svg = re.sub(r'(id="pag-lockup-check-badge">\s*<circle[^>]*?)fill="#00796B"', r'\1class="teal"', svg)
    svg = svg.replace('fill="#FFFFFF"', 'class="check"').replace('fill="#0B2A5B"', 'class="ink"')
    svg = svg.replace('fill="#00796B"', 'class="teal"')
    return svg


LOGO = _logo()


def page(language: str, title: str, body: str, refresh_script: str = "", token: str = "", nav: str = "") -> bytes:
    from pdfaccessguru import __version__

    t = TEXT[language]
    static = f"/{token}/static/" if token else ""
    home = f"/{token}/?lang={language}" if token else "#main"
    faces = FONT_FACES.replace("{static}", static) if token else ""
    icon = f'<link rel="icon" type="image/svg+xml" href="{static}icon.svg">' if token else ""
    document = f"""<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{html.escape(title)} – {t['title']}</title>
{icon}
<style>{faces}{CSS}</style>
</head>
<body>
<a class="skip" href="#main">{t['skip']}</a>
<header class="top"><div class="bar">
<a class="brand" href="{home}" aria-label="{t['home_label']}">{LOGO}</a>
{nav}
</div></header>
<main id="main" tabindex="-1">
{body}
</main>
<footer><p>{html.escape(t['footer'].format(version=__version__))}</p></footer>
{refresh_script}
</body>
</html>"""
    return document.encode("utf-8")
