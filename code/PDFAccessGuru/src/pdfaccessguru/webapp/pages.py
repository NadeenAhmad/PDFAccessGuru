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
        "tour_link": "Guided tour",
        "tour_count": "Step {n} of {total}",
        "tour_back": "Back",
        "tour_next": "Next",
        "tour_done": "Done",
        "tour_skip": "Skip the tour",
        "tour_steps": [
            ("Choose files", "Choose one or more PDF files. Your originals are never changed."),
            ("Descriptions", "Choose who writes the descriptions. For confidential files, choose one that stays on "
                             "your computer."),
            ("Colours", "Switch this on only if the colours of your file may change."),
            ("Report", "You always get a report. Add a review list if someone should review what the tool decided."),
            ("Protected files", "Only needed if your PDF has a password."),
            ("Start", "Click here. Then you can download the new PDF, review and correct the descriptions, and "
                      "see the reading order."),
        ],
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
        "n_check": "Texts to review",
        "next_steps": "Next steps",
        "download_pdf_short": "The accessible PDF",
        "report_pdf_note": "The report as an accessible PDF",
        "report_md_note": "The report as plain text, for editing or sharing",
        "check_note": "Picture descriptions, link texts, title, language, and what was hidden as decoration",
        "preview_note": "The new PDF as assistive technologies present it: in reading order, with headings and picture descriptions",
        "footer": "PDFAccessGuru {version}. Runs only on your computer. Free and open source.",
        "hero_title": "Make PDF files accessible",
        "promise_local": "Your files stay on your computer, unless you choose an online AI",
        "promise_standard": "Checked against PDF/UA, the standard for accessible PDF",
        "promise_original": "The original is never changed",
        "promise_free": "Free and open source",
        "intro": "Makes PDF files accessible to everyone.",
        "file_legend": "1. Choose PDF files",
        "file_label": "One or more PDF files",
        "file_help": "The original files are not changed. You get a new, improved copy of each. To choose several files, hold Ctrl (on a Mac: Cmd) while you click.",
        "ai_legend": "2. Choose who writes the descriptions",
        "ai_intro": "Descriptions tell people who can't see a picture what it shows, for example blind people who use "
                    "a screen reader. The tool also writes them for formulas, links and form fields.",
        "ai_group_local": "Stays on your computer (recommended for confidential files)",
        "ai_group_online": "Sent over the internet",
        "ai_ollama": "An AI on your computer (Ollama)",
        "ai_ollama_help": "Free and private. Nothing leaves your computer.",
        "ai_ollama_found": "Found on your computer: {model}",
        "ai_ollama_missing": "Not installed or not running. To use it, install Ollama from ollama.com, then run: "
                             "ollama pull gemma4:e4b",
        "ai_none": "No AI: simple rules",
        "ai_none_help": "Nothing leaves your computer. Fast, but the texts are less helpful.",
        "ai_cloud": "An online AI like ChatGPT",
        "ai_cloud_help": "Or Claude, Gemini and others through OpenRouter. Pictures and text from your file are sent "
                         "to that company. You need a key from them.",
        "ai_key_promise": "Your key stays in the settings file on your computer. PDFAccessGuru sends it only to that "
                          "company and never puts it into the PDF or the report.",
        "ai_key_found": "Key found: {name}",
        "ai_key_missing": "No key set up yet. Write OPENAI_API_KEY=your-key (or OPENROUTER_API_KEY=your-key) into "
                          "this file, then reload this page: {path}",
        "contrast_legend": "3. Colours",
        "contrast_label": "Improve colour contrast (changes text colours)",
        "contrast_help": "Makes text that is hard to read a little darker or lighter. Leave this off for "
                         "templates whose colours must not change, for example official templates.",
        "report_legend": "4. Report on the changes",
        "report_language": "With the new PDF you also get a report: a short document that says in plain words what "
                           "the tool fixed and what you still need to do. It is written in the language of the PDF.",
        "writing_report": "Writing the report",
        "n_files": "{n} files",
        "file_n_of": "File {n} of {total} ({name})",
        "download_zip": "All new files and reports in one ZIP file",
        "summary": "Passes the automatic check: {passes}. Problems fixed: {fixed}. Still open: {open}.",
        "yes": "yes", "no": "no",
        "show_report": "Show the report",
        "not_done": "Not processed, because the work was stopped.",
        "review_label": "Add a review list to the report",
        "review_help": "A list of everything the tool decided by itself, for example picture descriptions, the "
                       "title, the language and headings, so a person can review it. Going through it takes a few "
                       "minutes. You can also review and correct everything in the app after fixing.",
        "protected_legend": "5. Only for protected PDFs (optional)",
        "password_label": "Owner password of the PDF",
        "password_help": "Only needed if the file is protected and blocks screen readers and other assistive "
                         "technologies. The password is used "
                         "once and not stored.",
        "start": "Make the PDF accessible",
        "busy": "Another file is being worked on. Please wait until it is finished.",
        "working_title": "Working on {name}",
        "working_help": "This can take a few minutes for long files.",
        "progress_label": "Progress",
        "cancel": "Stop",
        "done_title": "Done: {name}",
        "downloads": "Downloads",
        "download_pdf": "The accessible PDF ({name}, {size})",
        "download_report_pdf": "Report (PDF)",
        "download_report_md": "Report (Markdown text)",
        "report": "Report",
        "again": "Make another PDF accessible",
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
        "updating": "PDFAccessGuru is being updated and opens again in about a minute (a few minutes on the day a new version comes out). You can close this tab.",
        "update_manual": "The update could not be started automatically. Run this in a terminal: pdfaccessguru update",
        "tools_needed": "Before the first use, PDFAccessGuru needs two free helper programs and some free fonts "
                        "(Java, veraPDF and the Liberation fonts, about 77 MB). They are downloaded once into "
                        "your user folder. No admin rights are needed.",
        "tools_button": "Download them now",
        "tools_working": "Downloading the helper programs: {text}",
        "tools_failed": "The helper programs could not be downloaded: {error}",
        "tools_done": "The helper programs are ready.",
        "check_link": "Review and correct the tool's choices",
        "preview_link": "Show the reading order",
        "check_title": "Review the tool's choices: {name}",
        "check_intro": "The tool wrote these texts and made these choices by itself. Correct anything that is wrong, then save. Your changes go "
                       "straight into the new PDF. To review a text, compare it with the text under its name "
                       "(the caption, the text nearby, or where a link goes).",
        "checked": "reviewed",
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
        "accept_pictures": "Save, and mark all picture descriptions as reviewed",
        "accept_formulas": "Save, and mark all formula descriptions as reviewed",
        "accept_links": "Save, and mark all link descriptions as reviewed",
        "accept_fields": "Save, and mark all form field descriptions as reviewed",
        "nothing_written": "The tool did not write any other texts for this file.",
        "save": "Save my changes",
        "back": "Back to the results",
        "changed_meanwhile": "The file was changed in the meantime, for example in another tab. Nothing was saved. Please review the texts again.",
        "empty_text": "A text cannot be empty. Nothing was saved.",
        "bad_language": "The language must be a short code like en, de or en-GB. Nothing was saved.",
        "saved": "Saved. The new PDF and the report now include your changes.",
        "preview_title": "Reading order: {name}",
        "preview_intro": "This is the new PDF as screen readers and read-aloud tools present it, in this order. Decoration is left out. Check "
                         "that the order and the headings make sense. Pictures are shown by their description.",
    },
    "de": {
        "title": "PDFAccessGuru",
        "skip": "Zum Hauptinhalt springen",
        "tour_link": "Rundgang",
        "tour_count": "Schritt {n} von {total}",
        "tour_back": "Zurück",
        "tour_next": "Weiter",
        "tour_done": "Fertig",
        "tour_skip": "Rundgang überspringen",
        "tour_steps": [
            ("Dateien wählen", "Wählen Sie eine oder mehrere PDF-Dateien. Ihre Originale werden nie verändert."),
            ("Beschreibungen", "Wählen Sie, wer die Beschreibungen schreibt. Für vertrauliche Dateien wählen Sie "
                               "eine Möglichkeit, die auf Ihrem Computer bleibt."),
            ("Farben", "Schalten Sie dies nur ein, wenn sich die Farben Ihrer Datei ändern dürfen."),
            ("Bericht", "Sie erhalten immer einen Bericht. Nehmen Sie eine Liste zum Durchsehen auf, wenn jemand "
                        "durchsehen soll, was das Werkzeug entschieden hat."),
            ("Geschützte Dateien", "Nur nötig, wenn Ihre PDF ein Kennwort hat."),
            ("Start", "Klicken Sie hier. Danach können Sie die neue PDF herunterladen, die Beschreibungen "
                      "durchsehen und korrigieren und die Lesereihenfolge ansehen."),
        ],
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
        "n_check": "Texte zum Durchsehen",
        "next_steps": "Nächste Schritte",
        "download_pdf_short": "Die barrierefreie PDF",
        "report_pdf_note": "Der Bericht als barrierefreie PDF",
        "report_md_note": "Der Bericht als reiner Text, zum Bearbeiten oder Weitergeben",
        "check_note": "Bildbeschreibungen, Linktexte, Titel, Sprache und was als Dekoration ausgeblendet wurde",
        "preview_note": "Die neue PDF so, wie assistive Technologien sie wiedergeben: in Lesereihenfolge, mit Überschriften und Bildbeschreibungen",
        "footer": "PDFAccessGuru {version}. Läuft nur auf Ihrem Computer. Kostenlos und quelloffen.",
        "hero_title": "PDF-Dateien barrierefrei machen",
        "promise_local": "Ihre Dateien bleiben auf Ihrem Computer, außer Sie wählen eine Online-KI",
        "promise_standard": "Geprüft nach PDF/UA, dem Standard für barrierefreie PDF",
        "promise_original": "Das Original wird nie verändert",
        "promise_free": "Kostenlos und quelloffen",
        "intro": "Macht PDF-Dateien für alle zugänglich.",
        "file_legend": "1. PDF-Dateien wählen",
        "file_label": "Eine oder mehrere PDF-Dateien",
        "file_help": "Die Originaldateien werden nicht verändert. Sie erhalten von jeder eine neue, verbesserte Kopie. Für mehrere Dateien halten Sie beim Klicken Strg gedrückt (auf dem Mac: Cmd).",
        "ai_legend": "2. Wählen Sie, wer die Beschreibungen schreibt",
        "ai_intro": "Beschreibungen sagen Menschen, die ein Bild nicht sehen können, was es zeigt, zum Beispiel "
                    "blinden Menschen, die einen Screenreader nutzen. Das Werkzeug schreibt sie auch für Formeln, "
                    "Links und Formularfelder.",
        "ai_group_local": "Bleibt auf Ihrem Computer (empfohlen für vertrauliche Dateien)",
        "ai_group_online": "Wird über das Internet gesendet",
        "ai_ollama": "Eine KI auf Ihrem Computer (Ollama)",
        "ai_ollama_help": "Kostenlos und privat. Nichts verlässt Ihren Computer.",
        "ai_ollama_found": "Auf Ihrem Computer gefunden: {model}",
        "ai_ollama_missing": "Nicht installiert oder nicht gestartet. Installieren Sie dafür Ollama von ollama.com "
                             "und geben Sie dann ein: ollama pull gemma4:e4b",
        "ai_none": "Keine KI: einfache Regeln",
        "ai_none_help": "Nichts verlässt Ihren Computer. Schnell, aber die Texte sind weniger hilfreich.",
        "ai_cloud": "Eine Online-KI wie ChatGPT",
        "ai_cloud_help": "Oder Claude, Gemini und andere über OpenRouter. Bilder und Text aus Ihrer Datei werden an "
                         "diese Firma gesendet. Sie brauchen einen Schlüssel von ihr.",
        "ai_key_promise": "Ihr Schlüssel bleibt in der Einstellungsdatei auf Ihrem Computer. PDFAccessGuru sendet ihn "
                          "nur an diese Firma und schreibt ihn nie in die PDF oder den Bericht.",
        "ai_key_found": "Schlüssel gefunden: {name}",
        "ai_key_missing": "Noch kein Schlüssel eingerichtet. Schreiben Sie OPENAI_API_KEY=Ihr-Schlüssel (oder "
                          "OPENROUTER_API_KEY=Ihr-Schlüssel) in diese Datei und laden Sie dann diese Seite neu: {path}",
        "contrast_legend": "3. Farben",
        "contrast_label": "Farbkontrast verbessern (ändert Textfarben)",
        "contrast_help": "Macht schwer lesbaren Text etwas dunkler oder heller. Lassen Sie "
                         "dies aus bei Vorlagen, deren Farben sich nicht ändern dürfen, zum Beispiel amtlichen "
                         "Vorlagen.",
        "report_legend": "4. Bericht über die Änderungen",
        "report_language": "Zusammen mit der neuen PDF erhalten Sie einen Bericht: ein kurzes Dokument, das in "
                           "einfachen Worten sagt, was das Werkzeug repariert hat und was Sie noch tun müssen. Er ist "
                           "in der Sprache der PDF geschrieben.",
        "writing_report": "Der Bericht wird geschrieben",
        "n_files": "{n} Dateien",
        "file_n_of": "Datei {n} von {total} ({name})",
        "download_zip": "Alle neuen Dateien und Berichte in einer ZIP-Datei",
        "summary": "Besteht die automatische Prüfung: {passes}. Behobene Probleme: {fixed}. Noch offen: {open}.",
        "yes": "ja", "no": "nein",
        "show_report": "Bericht zeigen",
        "not_done": "Nicht bearbeitet, weil die Arbeit abgebrochen wurde.",
        "review_label": "Eine Liste zum Durchsehen in den Bericht aufnehmen",
        "review_help": "Alles, was das Werkzeug selbst entschieden hat, zum Beispiel Bildbeschreibungen, Titel, "
                       "Sprache und Überschriften, damit eine Person es durchsehen kann. Das Durchgehen dauert einige "
                       "Minuten. Sie können nach dem Reparieren auch alles in der App durchsehen und korrigieren.",
        "protected_legend": "5. Nur für geschützte PDFs (optional)",
        "password_label": "Besitzerkennwort der PDF",
        "password_help": "Nur nötig, wenn die Datei geschützt ist und Screenreader und andere assistive Technologien "
                         "sperrt. Das Kennwort wird einmal "
                         "verwendet und nicht gespeichert.",
        "start": "PDF barrierefrei machen",
        "busy": "Gerade wird eine andere Datei bearbeitet. Bitte warten Sie, bis sie fertig ist.",
        "working_title": "{name} wird bearbeitet",
        "working_help": "Bei langen Dateien kann das einige Minuten dauern.",
        "progress_label": "Fortschritt",
        "cancel": "Abbrechen",
        "done_title": "Fertig: {name}",
        "downloads": "Herunterladen",
        "download_pdf": "Die barrierefreie PDF ({name}, {size})",
        "download_report_pdf": "Bericht (PDF)",
        "download_report_md": "Bericht (Markdown-Text)",
        "report": "Bericht",
        "again": "Weitere PDF barrierefrei machen",
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
        "updating": "PDFAccessGuru wird aktualisiert und öffnet sich in etwa einer Minute wieder (am Tag einer neuen Version einige Minuten). Sie können diesen Tab schließen.",
        "update_manual": "Die Aktualisierung ließ sich nicht automatisch starten. Geben Sie im Terminal ein: pdfaccessguru update",
        "tools_needed": "Vor der ersten Verwendung braucht PDFAccessGuru zwei kostenlose Hilfsprogramme und einige "
                        "kostenlose Schriften (Java, veraPDF und die Liberation-Schriften, etwa 77 MB). Sie werden "
                        "einmal in Ihren Benutzerordner geladen. Es sind keine Administratorrechte nötig.",
        "tools_button": "Jetzt herunterladen",
        "tools_working": "Die Hilfsprogramme werden geladen: {text}",
        "tools_failed": "Die Hilfsprogramme konnten nicht geladen werden: {error}",
        "tools_done": "Die Hilfsprogramme sind bereit.",
        "check_link": "Die Entscheidungen des Werkzeugs durchsehen und korrigieren",
        "preview_link": "Lesereihenfolge zeigen",
        "check_title": "Entscheidungen durchsehen: {name}",
        "check_intro": "Diese Texte und Entscheidungen stammen vom Werkzeug selbst. Korrigieren Sie, was nicht stimmt, und "
                       "speichern Sie. Ihre Änderungen kommen direkt in die neue PDF. Zum Durchsehen vergleichen Sie den "
                       "Text mit dem Text unter seinem Namen (Bildunterschrift, Text in der Nähe oder Linkziel).",
        "checked": "durchgesehen",
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
        "accept_pictures": "Speichern und alle Bildbeschreibungen als durchgesehen markieren",
        "accept_formulas": "Speichern und alle Formelbeschreibungen als durchgesehen markieren",
        "accept_links": "Speichern und alle Linkbeschreibungen als durchgesehen markieren",
        "accept_fields": "Speichern und alle Beschreibungen von Formularfeldern als durchgesehen markieren",
        "nothing_written": "Das Werkzeug hat für diese Datei keine weiteren Texte geschrieben.",
        "save": "Meine Änderungen speichern",
        "back": "Zurück zu den Ergebnissen",
        "changed_meanwhile": "Die Datei wurde inzwischen geändert, zum Beispiel in einem anderen Tab. Es wurde nichts gespeichert. Bitte sehen Sie die Texte erneut durch.",
        "empty_text": "Ein Text darf nicht leer sein. Es wurde nichts gespeichert.",
        "bad_language": "Die Sprache muss ein kurzer Code sein, z. B. de, en oder de-AT. Es wurde nichts gespeichert.",
        "saved": "Gespeichert. Die neue PDF und der Bericht enthalten jetzt Ihre Änderungen.",
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
footer { color: var(--muted); font-size: 1.2rem; padding-bottom: 2rem; }
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
.choice { position: relative; display: flex; gap: .75rem; align-items: flex-start; margin: .6rem 0; padding: .8rem 1rem;
          border: 2px solid var(--soft); border-radius: .7rem; }
.choice:has(input:checked) { border-color: var(--teal); background: var(--ok-bg); }
.choice:has(input:focus-visible) { outline: 3px solid var(--focus); outline-offset: 3px; }
.choice:has(input:disabled) { border-style: dashed; }
.choice input { width: 1.35rem; height: 1.35rem; margin-top: .25rem; flex: none; accent-color: var(--teal); }
.choice input:focus-visible { outline: none; }
.choice label { font-weight: 700; }
.choice label::after { content: ""; position: absolute; inset: 0; cursor: pointer; }   /* the whole box is clickable */
.choice:has(input:disabled) label::after { display: none; }   /* so the set-up hint can be selected and copied */
.choice .help { margin: .2rem 0 0; }
.choice .help span { display: block; margin-top: .25rem; }
.choice .help .state { color: var(--ink); font-weight: 700; }
h3.group { font-size: 1.1rem; margin: 1.1rem 0 .2rem; }
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
.progress-head { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; margin-bottom: .3rem; }
#percent { font-weight: 700; font-size: 1.2rem; color: var(--navy); font-variant-numeric: tabular-nums; }
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
[hidden] { display: none !important; }
.top .tools { display: flex; align-items: center; gap: 1.4rem; flex-wrap: wrap; }
.tour-link { font-weight: 700; }
dialog.tour { position: fixed; margin: 0; top: 6rem; left: 50%; width: min(26rem, calc(100% - 2rem)); padding: 1.2rem 1.4rem;
              border: 2px solid var(--teal); border-radius: 1rem; background: var(--card); color: var(--ink);
              box-shadow: 0 12px 32px rgba(0, 0, 0, .35); }
dialog.tour::backdrop { background: transparent; }
dialog.tour h2 { margin: .15rem 0 .4rem; }
dialog.tour p { margin: 0; }
.tour-count { color: var(--muted); font-size: 1rem; }
.tour-buttons { display: flex; flex-wrap: wrap; gap: .6rem; margin-top: 1.1rem; }
.tour-buttons button { font-size: 1.05rem; padding: .6rem 1.1rem; }
button.plain { background: none; border-color: transparent; color: var(--link); text-decoration: underline; }
.tour-spot { position: absolute; z-index: 50; border-radius: 1rem; pointer-events: none;
             box-shadow: 0 0 0 200vmax rgba(8, 14, 24, .62); outline: 3px solid var(--focus); outline-offset: 2px; }
@media (prefers-reduced-motion: no-preference) { .tour-spot { transition: top .25s, left .25s, width .25s, height .25s; } }
@media (max-width: 40rem) { dialog.tour { top: auto !important; bottom: 1rem; left: 1rem !important; width: calc(100% - 2rem); } }
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


def choice(kind: str, name: str, value: str, ident: str, label: str, lines: list[str], checked: bool = False,
           disabled: bool = False) -> str:
    """
    One option box: the input, its bold label and its explanation inside the box (connected with
    aria-describedby). The whole box can be clicked. With more than one line, the last line says
    what is set up on this computer.
    """
    parts = [f'<span class="state">{html.escape(line)}</span>' if index == len(lines) - 1 and len(lines) > 1
             else f"<span>{html.escape(line)}</span>" for index, line in enumerate(lines)]
    flags = (" checked" if checked else "") + (" disabled" if disabled else "")
    return (f'  <div class="choice"><input type="{kind}" id="{ident}" name="{name}" value="{value}"{flags} '
            f'aria-describedby="{ident}-help"><div><label for="{ident}">{html.escape(label)}</label>'
            f'<p class="help" id="{ident}-help">{"".join(parts)}</p></div></div>')


def page(language: str, title: str, body: str, refresh_script: str = "", token: str = "", nav: str = "") -> bytes:
    from pdfaccessguru import __version__

    t = TEXT[language]
    static = f"/{token}/static/" if token else ""
    home = f"/{token}/?lang={language}" if token else "#main"
    faces = FONT_FACES.replace("{static}", static) if token else ""
    icon = f'<link rel="icon" type="image/svg+xml" href="{static}icon.svg">' if token else ""
    tour = f'<a class="tour-link" id="tour-open" href="/{token}/?lang={language}&amp;tour=1">{t["tour_link"]}</a>' if token else ""
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
<div class="tools">{tour}{nav}</div>
</div></header>
<main id="main" tabindex="-1">
{body}
</main>
<footer><p>{html.escape(t['footer'].format(version=__version__))}</p></footer>
{refresh_script}
</body>
</html>"""
    return document.encode("utf-8")


def tour(language: str, token: str, auto: bool) -> str:
    """
    The guided tour of the start page (Phase 12c): a dialog next to each part, the rest of the page
    shaded. It starts by itself the first time (auto) and from the "Guided tour" link at any time.
    Keyboard and screen reader: a modal dialog (Esc closes it, focus stays inside and returns
    afterwards); each new step is announced politely. No movement for people who turn motion off.
    """
    import json

    t = TEXT[language]
    data = json.dumps({"steps": t["tour_steps"], "count": t["tour_count"], "next": t["tour_next"],
                       "done": t["tour_done"], "auto": auto, "seen": f"/{token}/tour-seen"})
    return f"""<dialog class="tour" id="tour" aria-labelledby="tour-title" aria-describedby="tour-text">
<div aria-live="polite"><p class="tour-count" id="tour-count"></p><h2 id="tour-title"></h2><p id="tour-text"></p></div>
<div class="tour-buttons"><button type="button" class="secondary" id="tour-back">{t['tour_back']}</button>
<button type="button" id="tour-next">{t['tour_next']}</button>
<button type="button" class="plain" id="tour-skip">{t['tour_skip']}</button></div>
</dialog>
<div class="tour-spot" id="tour-spot" hidden></div>
<script>
(function () {{
  var data = {data};
  var dialog = document.getElementById("tour"), spot = document.getElementById("tour-spot");
  if (!dialog || !dialog.showModal) return;
  var $ = function (id) {{ return document.getElementById(id); }};
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var index = 0, opener = null, total = data.steps.length;
  function target() {{ return $("tour-" + (index + 1)); }}
  var wide = function () {{ return window.innerWidth > 640; }};
  function place() {{
    var element = target();
    if (!element || !dialog.open) return;
    var box = element.getBoundingClientRect(), pad = 8;
    spot.style.top = (box.top + window.scrollY - pad) + "px";
    spot.style.left = (box.left + window.scrollX - pad) + "px";
    spot.style.width = (box.width + 2 * pad) + "px";
    spot.style.height = (box.height + 2 * pad) + "px";
    if (wide()) {{                        /* above the part if there is room, else below, else at the top */
      var height = dialog.offsetHeight, width = dialog.offsetWidth;
      var top = box.top - pad - 14 - height;
      if (top < 8) top = box.bottom + pad + 14 + height < window.innerHeight - 8 ? box.bottom + pad + 14 : 8;
      dialog.style.top = top + "px";
      dialog.style.left = Math.max(8, Math.min(box.left, window.innerWidth - width - 8)) + "px";
    }}
  }}
  function bring() {{                     /* scroll the part to just below the dialog (or to the top on phones) */
    var element = target(), offset = wide() ? dialog.offsetHeight + 36 : 16;
    var top = element.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({{top: Math.max(0, top), behavior: reduce ? "auto" : "smooth"}});
  }}
  function show(number) {{
    index = number;
    $("tour-count").textContent = data.count.replace("{{n}}", number + 1).replace("{{total}}", total);
    $("tour-title").textContent = data.steps[number][0];
    $("tour-text").textContent = data.steps[number][1];
    $("tour-back").hidden = number === 0;
    $("tour-skip").hidden = number === total - 1;
    $("tour-next").textContent = number === total - 1 ? data.done : data.next;
    bring();
    spot.hidden = false;
    place();
    setTimeout(place, reduce ? 0 : 450);
    $("tour-next").focus();
  }}
  function start() {{
    opener = document.activeElement;
    if (!dialog.open) dialog.showModal();
    show(0);
    fetch(data.seen, {{method: "POST"}}).catch(function () {{}});
  }}
  dialog.addEventListener("close", function () {{
    spot.hidden = true;
    var back = $("tour-open");
    (opener && opener !== document.body ? opener : back).focus();
  }});
  $("tour-next").addEventListener("click", function () {{ if (index < total - 1) show(index + 1); else dialog.close(); }});
  $("tour-back").addEventListener("click", function () {{ if (index > 0) show(index - 1); }});
  $("tour-skip").addEventListener("click", function () {{ dialog.close(); }});
  window.addEventListener("resize", place);
  window.addEventListener("scroll", place, {{passive: true}});
  var link = $("tour-open");
  if (link) link.addEventListener("click", function (event) {{ event.preventDefault(); start(); }});
  var asked = new URLSearchParams(window.location.search).get("tour") === "1";
  if (asked) history.replaceState(null, "", window.location.pathname + "?lang=" + document.documentElement.lang);
  if (data.auto || asked) start();
}})();
</script>"""
