"""
Plain names and short explanations of every problem, in English and German (Phase 7a).

Reports and the app show these instead of internal names like "content-neither-artifact-nor-
tagged-content". Each entry: (name EN, name DE, why it matters EN, why it matters DE).
TODO holds what the author can do for problems that often stay open.
"""

from __future__ import annotations

# rule id: (name_en, name_de, why_en, why_de)
PROBLEMS: dict[str, tuple[str, str, str, str]] = {
    # file information
    "5-1": ("PDF/UA label missing", "PDF/UA-Kennzeichnung fehlt",
            "The file does not say that it follows the accessibility standard PDF/UA.",
            "Die Datei gibt nicht an, dass sie dem Barrierefreiheits-Standard PDF/UA folgt."),
    "5-2": ("PDF/UA label wrong", "PDF/UA-Kennzeichnung fehlerhaft",
            "The PDF/UA version number in the file information is wrong.",
            "Die PDF/UA-Versionsnummer in den Dateiinformationen ist falsch."),
    "5-3": ("PDF/UA label written wrongly", "PDF/UA-Kennzeichnung falsch geschrieben",
            "The PDF/UA label uses a wrong technical name, so programs do not find it.",
            "Die PDF/UA-Kennzeichnung verwendet einen falschen technischen Namen, Programme finden sie nicht."),
    "5-4": ("PDF/UA amendment entry wrong", "PDF/UA-Ergänzungsangabe fehlerhaft",
            "An optional entry of the PDF/UA label is written wrongly.",
            "Eine optionale Angabe der PDF/UA-Kennzeichnung ist falsch geschrieben."),
    "5-5": ("PDF/UA correction entry wrong", "PDF/UA-Korrekturangabe fehlerhaft",
            "An optional entry of the PDF/UA label is written wrongly.",
            "Eine optionale Angabe der PDF/UA-Kennzeichnung ist falsch geschrieben."),
    "6.1-1": ("PDF version not suitable", "PDF-Version nicht passend",
              "The file uses a PDF version that does not fit the accessibility check.",
              "Die Datei verwendet eine PDF-Version, die nicht zur Barrierefreiheitsprüfung passt."),
    "6.2-1": ("File not marked as tagged", "Datei nicht als getaggt markiert",
              "The file does not say that it has tags, so screen readers may ignore them.",
              "Die Datei gibt nicht an, dass sie Tags hat; Screenreader ignorieren sie dann womöglich."),
    "7.1-8": ("File information missing", "Dateiinformationen fehlen",
              "The file has no information block (title, language, standard).",
              "Die Datei hat keinen Informationsblock (Titel, Sprache, Standard)."),
    "7.1-9": ("Title missing", "Titel fehlt",
              "The document has no title. Screen readers announce the title when the file is opened.",
              "Das Dokument hat keinen Titel. Screenreader lesen den Titel beim Öffnen vor."),
    "7.1-10": ("Title not shown in the window", "Titel wird im Fenster nicht angezeigt",
               "Viewers show the file name instead of the title, which is often unclear.",
               "Programme zeigen den Dateinamen statt des Titels, der oft nichtssagend ist."),
    # tags and content
    "7.1-1": ("Decoration inside real content", "Dekoration in echtem Inhalt",
              "Something marked as decoration sits inside tagged content, which confuses screen readers.",
              "Etwas als Dekoration Markiertes steckt in getaggtem Inhalt; das verwirrt Screenreader."),
    "7.1-2": ("Content is both decoration and tagged", "Inhalt ist zugleich Dekoration und getaggt",
              "Content is marked as decoration and also tagged, so it is unclear whether it is read.",
              "Inhalt ist als Dekoration markiert und zugleich getaggt; unklar, ob er vorgelesen wird."),
    "7.1-3": ("Content without tag", "Inhalt ohne Tag",
              "Text or pictures are neither tagged nor marked as decoration, so screen readers may skip them.",
              "Text oder Bilder sind weder getaggt noch als Dekoration markiert; Screenreader überspringen sie womöglich."),
    "7.1-4": ("Tags marked as unchecked", "Tags als ungeprüft markiert",
              "The program that made the tags was not sure they are right.",
              "Das Programm, das die Tags erstellt hat, war sich nicht sicher, ob sie stimmen."),
    "7.1-5": ("Tag type without standard meaning", "Tag-Typ ohne Standardbedeutung",
              "A tag has a custom name that screen readers do not understand.",
              "Ein Tag hat einen eigenen Namen, den Screenreader nicht verstehen."),
    "7.1-6": ("Tag types point to each other", "Tag-Typen verweisen im Kreis",
              "Custom tag names refer to each other in a circle and never reach a known meaning.",
              "Eigene Tag-Namen verweisen im Kreis aufeinander und erreichen nie eine bekannte Bedeutung."),
    "7.1-7": ("Standard tag type changed", "Standard-Tag-Typ umgedeutet",
              "A standard tag (like 'paragraph') is redefined, which changes how it is read.",
              "Ein Standard-Tag (z. B. 'Absatz') ist umgedeutet; das ändert, wie er vorgelesen wird."),
    "7.1-11": ("No tags at all", "Gar keine Tags",
               "The file has no tags. Screen readers cannot tell headings, lists or tables apart.",
               "Die Datei hat keine Tags. Screenreader erkennen keine Überschriften, Listen oder Tabellen."),
    "7.1-12": ("Tag without parent link", "Tag ohne Verbindung nach oben",
               "A tag does not know which tag it belongs to, which breaks the reading structure.",
               "Ein Tag weiß nicht, zu welchem Tag er gehört; das stört die Lesestruktur."),
    # language
    "7.2-2": ("Language of the bookmarks unknown", "Sprache der Lesezeichen unbekannt",
              "Screen readers do not know in which language to read the bookmarks.",
              "Screenreader wissen nicht, in welcher Sprache sie die Lesezeichen vorlesen sollen."),
    "7.2-21": ("Language of replacement text unknown", "Sprache des Ersatztextes unbekannt",
               "A replacement text has no language, so it may be pronounced wrongly.",
               "Ein Ersatztext hat keine Sprache und wird womöglich falsch ausgesprochen."),
    "7.2-22": ("Language of a description unknown", "Sprache einer Beschreibung unbekannt",
               "A picture or element description has no language, so it may be pronounced wrongly.",
               "Eine Bild- oder Elementbeschreibung hat keine Sprache und wird womöglich falsch ausgesprochen."),
    "7.2-23": ("Language of an abbreviation unknown", "Sprache einer Abkürzung unbekannt",
               "The written-out form of an abbreviation has no language.",
               "Die ausgeschriebene Form einer Abkürzung hat keine Sprache."),
    "7.2-24": ("Language of a comment unknown", "Sprache eines Kommentars unbekannt",
               "A comment or link description has no language.",
               "Ein Kommentar oder eine Linkbeschreibung hat keine Sprache."),
    "7.2-25": ("Language of a form field name unknown", "Sprache eines Formularfeldnamens unbekannt",
               "A form field name has no language.", "Ein Formularfeldname hat keine Sprache."),
    "7.2-29": ("Language code invalid", "Sprachcode ungültig",
               "A language is given with a code that does not exist.",
               "Eine Sprache ist mit einem Code angegeben, den es nicht gibt."),
    "7.2-30": ("Language of replacement text unknown", "Sprache des Ersatztextes unbekannt",
               "A replacement text inside a line has no language.",
               "Ein Ersatztext innerhalb einer Zeile hat keine Sprache."),
    "7.2-31": ("Language of a description unknown", "Sprache einer Beschreibung unbekannt",
               "A description inside a line has no language.", "Eine Beschreibung innerhalb einer Zeile hat keine Sprache."),
    "7.2-32": ("Language of an abbreviation unknown", "Sprache einer Abkürzung unbekannt",
               "The written-out form of an abbreviation inside a line has no language.",
               "Die ausgeschriebene Form einer Abkürzung in einer Zeile hat keine Sprache."),
    "7.2-33": ("Language of the file information unknown", "Sprache der Dateiinformationen unbekannt",
               "Title and description of the file have no language.",
               "Titel und Beschreibung der Datei haben keine Sprache."),
    "7.2-34": ("Language of the text unknown", "Sprache des Textes unbekannt",
               "Screen readers do not know which language to use, so they may pronounce the text wrongly.",
               "Screenreader wissen nicht, welche Sprache sie verwenden sollen, und sprechen den Text womöglich falsch aus."),
    # tables
    "7.2-3": ("Wrong content directly in a table", "Falscher Inhalt direkt in einer Tabelle",
              "A table contains something other than rows, row groups and a caption.",
              "Eine Tabelle enthält etwas anderes als Zeilen, Zeilengruppen und eine Beschriftung."),
    "7.2-4": ("Table row outside a table", "Tabellenzeile außerhalb einer Tabelle",
              "A row is not inside a table, so it is not read as part of one.",
              "Eine Zeile steht nicht in einer Tabelle und wird nicht als Teil davon vorgelesen."),
    "7.2-5": ("Table header group outside a table", "Tabellenkopf außerhalb einer Tabelle",
              "A header row group is not inside a table.", "Eine Kopfzeilengruppe steht nicht in einer Tabelle."),
    "7.2-6": ("Table body outside a table", "Tabellenkörper außerhalb einer Tabelle",
              "A group of table rows is not inside a table.", "Eine Gruppe von Tabellenzeilen steht nicht in einer Tabelle."),
    "7.2-7": ("Table footer outside a table", "Tabellenfuß außerhalb einer Tabelle",
              "A footer row group is not inside a table.", "Eine Fußzeilengruppe steht nicht in einer Tabelle."),
    "7.2-8": ("Header cell outside a row", "Kopfzelle außerhalb einer Zeile",
              "A header cell is not inside a table row, so its row and column are unknown.",
              "Eine Kopfzelle steht in keiner Tabellenzeile; Zeile und Spalte sind unbekannt."),
    "7.2-9": ("Cell outside a row", "Zelle außerhalb einer Zeile",
              "A table cell is not inside a row, so its row and column are unknown.",
              "Eine Tabellenzelle steht in keiner Zeile; Zeile und Spalte sind unbekannt."),
    "7.2-10": ("Wrong content in a table row", "Falscher Inhalt in einer Tabellenzeile",
               "A table row contains something other than cells.",
               "Eine Tabellenzeile enthält etwas anderes als Zellen."),
    "7.2-11": ("Table has several header groups", "Tabelle hat mehrere Kopfbereiche",
               "A table may have only one header row group.", "Eine Tabelle darf nur einen Kopfbereich haben."),
    "7.2-12": ("Table has several footer groups", "Tabelle hat mehrere Fußbereiche",
               "A table may have only one footer row group.", "Eine Tabelle darf nur einen Fußbereich haben."),
    "7.2-13": ("Table footer without body", "Tabellenfuß ohne Tabellenkörper",
               "A table with a footer group must also have a body group.",
               "Eine Tabelle mit Fußbereich braucht auch einen Tabellenkörper."),
    "7.2-14": ("Table header without body", "Tabellenkopf ohne Tabellenkörper",
               "A table with a header group must also have a body group.",
               "Eine Tabelle mit Kopfbereich braucht auch einen Tabellenkörper."),
    "7.2-15": ("Table cells overlap", "Tabellenzellen überlappen",
               "Table cells cover the same place, so screen readers cannot tell rows and columns apart.",
               "Tabellenzellen überdecken sich; Screenreader können Zeilen und Spalten nicht unterscheiden."),
    "7.2-16": ("Table caption in the wrong place", "Tabellenbeschriftung an falscher Stelle",
               "A table caption must be the first or last part of the table.",
               "Eine Tabellenbeschriftung muss am Anfang oder Ende der Tabelle stehen."),
    "7.2-36": ("Wrong content in a table header", "Falscher Inhalt im Tabellenkopf",
               "A table header group contains something other than rows.",
               "Ein Tabellenkopf enthält etwas anderes als Zeilen."),
    "7.2-37": ("Wrong content in a table body", "Falscher Inhalt im Tabellenkörper",
               "A table body contains something other than rows.",
               "Ein Tabellenkörper enthält etwas anderes als Zeilen."),
    "7.2-38": ("Wrong content in a table footer", "Falscher Inhalt im Tabellenfuß",
               "A table footer group contains something other than rows.",
               "Ein Tabellenfuß enthält etwas anderes als Zeilen."),
    "7.2-39": ("Table has several captions", "Tabelle hat mehrere Beschriftungen",
               "A table may have only one caption.", "Eine Tabelle darf nur eine Beschriftung haben."),
    "7.2-41": ("Table rows have different lengths", "Tabellenzeilen unterschiedlich lang",
               "Columns have different numbers of rows, so cells cannot be matched to their headers.",
               "Spalten haben unterschiedlich viele Zeilen; Zellen lassen sich ihren Überschriften nicht zuordnen."),
    "7.2-42": ("Table rows have different widths", "Tabellenzeilen unterschiedlich breit",
               "Rows have different numbers of columns, so cells cannot be matched to their headers.",
               "Zeilen haben unterschiedlich viele Spalten; Zellen lassen sich ihren Überschriften nicht zuordnen."),
    "7.2-43": ("Table rows have different widths", "Tabellenzeilen unterschiedlich breit",
               "Rows have different numbers of columns, so cells cannot be matched to their headers.",
               "Zeilen haben unterschiedlich viele Spalten; Zellen lassen sich ihren Überschriften nicht zuordnen."),
    "7.5-1": ("Table cell not linked to its header", "Tabellenzelle nicht mit Überschrift verbunden",
              "Screen readers cannot say which column or row header a cell belongs to.",
              "Screenreader können nicht sagen, zu welcher Spalten- oder Zeilenüberschrift eine Zelle gehört."),
    "7.5-2": ("Table cell linked to a missing header", "Tabellenzelle verweist auf fehlende Überschrift",
              "A cell refers to a header that does not exist.", "Eine Zelle verweist auf eine Überschrift, die es nicht gibt."),
    # lists, contents, headings
    "7.2-17": ("List item outside a list", "Listenpunkt außerhalb einer Liste",
               "A list item is not inside a list, so screen readers do not announce the list.",
               "Ein Listenpunkt steht in keiner Liste; Screenreader kündigen die Liste nicht an."),
    "7.2-18": ("List text outside a list item", "Listentext außerhalb eines Listenpunkts",
               "The text of a list item is not inside the item.", "Der Text eines Listenpunkts steht nicht im Listenpunkt."),
    "7.2-19": ("Wrong content in a list", "Falscher Inhalt in einer Liste",
               "A list contains something other than list items.", "Eine Liste enthält etwas anderes als Listenpunkte."),
    "7.2-20": ("Wrong content in a list item", "Falscher Inhalt in einem Listenpunkt",
               "A list item contains something other than its bullet and its text.",
               "Ein Listenpunkt enthält etwas anderes als Aufzählungszeichen und Text."),
    "7.2-40": ("List caption in the wrong place", "Listenbeschriftung an falscher Stelle",
               "A list caption must come first in the list.", "Eine Listenbeschriftung muss am Anfang der Liste stehen."),
    "7.2-26": ("Contents entry outside the table of contents", "Inhaltsverzeichniseintrag außerhalb des Verzeichnisses",
               "An entry is not inside a table of contents.", "Ein Eintrag steht in keinem Inhaltsverzeichnis."),
    "7.2-27": ("Wrong content in the table of contents", "Falscher Inhalt im Inhaltsverzeichnis",
               "A table of contents contains something other than entries.",
               "Ein Inhaltsverzeichnis enthält etwas anderes als Einträge."),
    "7.2-28": ("Contents caption in the wrong place", "Beschriftung des Inhaltsverzeichnisses an falscher Stelle",
               "A table-of-contents caption must come first.", "Eine Beschriftung des Inhaltsverzeichnisses muss am Anfang stehen."),
    "7.4.2-1": ("Heading level skipped", "Überschriftenebene übersprungen",
                "Headings jump a level (e.g. from level 1 to 3), which makes the outline confusing.",
                "Überschriften springen eine Ebene (z. B. von 1 auf 3); die Gliederung wird unklar."),
    "7.4.4-1": ("Two headings in one section", "Zwei Überschriften in einem Abschnitt",
                "A section has more than one heading of the same kind.", "Ein Abschnitt hat mehr als eine gleichartige Überschrift."),
    "7.4.4-2": ("Two kinds of headings mixed", "Zwei Arten von Überschriften gemischt",
                "The document mixes numbered and unnumbered headings, so levels are unclear.",
                "Das Dokument mischt nummerierte und unnummerierte Überschriften; die Ebenen sind unklar."),
    "7.4.4-3": ("Two kinds of headings mixed", "Zwei Arten von Überschriften gemischt",
                "The document mixes numbered and unnumbered headings, so levels are unclear.",
                "Das Dokument mischt nummerierte und unnummerierte Überschriften; die Ebenen sind unklar."),
    # pictures, formulas, notes
    "7.3-1": ("Picture without a description", "Bild ohne Beschreibung",
              "A screen reader cannot say what the picture shows.", "Ein Screenreader kann nicht sagen, was das Bild zeigt."),
    "7.7-1": ("Formula without a description", "Formel ohne Beschreibung",
              "A screen reader cannot read the formula aloud.", "Ein Screenreader kann die Formel nicht vorlesen."),
    "7.9-1": ("Footnote without an ID", "Fußnote ohne Kennung",
              "A footnote has no ID, so links to it cannot work.", "Eine Fußnote hat keine Kennung; Verweise darauf funktionieren nicht."),
    "7.9-2": ("Two footnotes with the same ID", "Zwei Fußnoten mit derselben Kennung",
              "Two footnotes share one ID, so links may lead to the wrong one.",
              "Zwei Fußnoten teilen eine Kennung; Verweise führen womöglich zur falschen."),
    # document settings
    "7.10-1": ("Layer without a name", "Ebene ohne Namen",
               "A layer of the document has no name, so users cannot tell what it is.",
               "Eine Ebene des Dokuments hat keinen Namen; Nutzer wissen nicht, was sie ist."),
    "7.10-2": ("Unsupported layer setting", "Nicht erlaubte Ebeneneinstellung",
               "The document uses a layer setting that the standard does not allow.",
               "Das Dokument verwendet eine Ebeneneinstellung, die der Standard nicht erlaubt."),
    "7.11-1": ("Attached file name incomplete", "Name einer angehängten Datei unvollständig",
               "An attached file is missing the second form of its name.",
               "Bei einer angehängten Datei fehlt die zweite Form ihres Namens."),
    "7.15-1": ("Dynamic form (XFA)", "Dynamisches Formular (XFA)",
               "The file uses a dynamic form type that screen readers do not support.",
               "Die Datei verwendet einen dynamischen Formulartyp, den Screenreader nicht unterstützen."),
    "7.16-1": ("Protection blocks screen readers", "Schutz sperrt Screenreader",
               "The file's protection settings do not let screen readers read the text.",
               "Die Schutzeinstellungen der Datei lassen Screenreader den Text nicht lesen."),
    # annotations, links, forms
    "7.18.1-1": ("Comment not in the tags", "Kommentar nicht in den Tags",
                 "A comment or other annotation is not part of the reading structure.",
                 "Ein Kommentar oder eine andere Anmerkung ist nicht Teil der Lesestruktur."),
    "7.18.1-2": ("Annotation without a description", "Anmerkung ohne Beschreibung",
                 "A screen reader cannot say what the link, comment or note is.",
                 "Ein Screenreader kann nicht sagen, was der Link, Kommentar oder Hinweis ist."),
    "7.18.1-3": ("Form field without a name", "Formularfeld ohne Namen",
                 "A screen reader cannot say what to enter in the field.",
                 "Ein Screenreader kann nicht sagen, was in das Feld einzutragen ist."),
    "7.18.2-1": ("Printing marks present", "Druckmarken vorhanden",
                 "The file contains a printing-only annotation type that is not allowed.",
                 "Die Datei enthält eine nur für den Druck gedachte Anmerkung, die nicht erlaubt ist."),
    "7.18.3-1": ("Tab order not set", "Tab-Reihenfolge nicht festgelegt",
                 "Pressing Tab may jump between links and fields in a confusing order.",
                 "Mit der Tab-Taste springt man womöglich in verwirrender Reihenfolge zwischen Links und Feldern."),
    "7.18.4-1": ("Form field not in the tags", "Formularfeld nicht in den Tags",
                 "A form field is not part of the reading structure.", "Ein Formularfeld ist nicht Teil der Lesestruktur."),
    "7.18.4-2": ("Form field tag wrong", "Formularfeld-Tag fehlerhaft",
                 "A form field tag contains more than its field.", "Ein Formularfeld-Tag enthält mehr als sein Feld."),
    "7.18.5-1": ("Link not in the tags", "Link nicht in den Tags",
                 "A link is not part of the reading structure, so screen readers may not find it.",
                 "Ein Link ist nicht Teil der Lesestruktur; Screenreader finden ihn womöglich nicht."),
    "7.18.5-2": ("Link without a description", "Link ohne Beschreibung",
                 "A screen reader cannot say where the link goes.", "Ein Screenreader kann nicht sagen, wohin der Link führt."),
    "7.18.6.2-1": ("Media without a type", "Medien ohne Typangabe",
                   "Embedded audio or video does not say what kind of media it is.",
                   "Eingebettetes Audio oder Video gibt nicht an, um welche Art Medium es sich handelt."),
    "7.18.6.2-2": ("Media without a description", "Medien ohne Beschreibung",
                   "Embedded audio or video has no description.", "Eingebettetes Audio oder Video hat keine Beschreibung."),
    "7.18.8-1": ("Printer's mark in the tags", "Druckermarke in den Tags",
                 "A printer's mark is part of the reading structure, but it is not content.",
                 "Eine Druckermarke ist Teil der Lesestruktur, obwohl sie kein Inhalt ist."),
    "7.20-1": ("Reference to another file's content", "Verweis auf Inhalt einer anderen Datei",
               "The file shows content from another file, which screen readers cannot reach.",
               "Die Datei zeigt Inhalt aus einer anderen Datei, den Screenreader nicht erreichen."),
    "7.20-2": ("Shared drawing tagged twice", "Gemeinsame Zeichnung doppelt getaggt",
               "A drawing used several times carries the same tags each time, which confuses screen readers.",
               "Eine mehrfach verwendete Zeichnung trägt jedes Mal dieselben Tags; das verwirrt Screenreader."),
    # fonts and characters
    "7.21.3.1-1": ("Font character set does not match", "Zeichensatz der Schrift passt nicht",
                   "Two parts of a composite font describe different character sets.",
                   "Zwei Teile einer zusammengesetzten Schrift beschreiben unterschiedliche Zeichensätze."),
    "7.21.3.2-1": ("Font glyph map missing", "Glyphenzuordnung der Schrift fehlt",
                   "A font does not say which shape belongs to which character code.",
                   "Eine Schrift gibt nicht an, welche Form zu welchem Zeichencode gehört."),
    "7.21.3.3-1": ("Font character map not in the file", "Zeichentabelle der Schrift nicht in der Datei",
                   "A character table that a font needs is not included in the file.",
                   "Eine Zeichentabelle, die eine Schrift braucht, ist nicht in der Datei enthalten."),
    "7.21.3.3-2": ("Font writing direction contradicts itself", "Schreibrichtung der Schrift widersprüchlich",
                   "A font gives two different writing directions.", "Eine Schrift gibt zwei verschiedene Schreibrichtungen an."),
    "7.21.3.3-3": ("Font character map refers to another one", "Zeichentabelle verweist auf eine andere",
                   "A character table depends on another one that is not standard.",
                   "Eine Zeichentabelle hängt von einer anderen ab, die nicht Standard ist."),
    "7.21.4.1-1": ("Font not embedded", "Schrift nicht eingebettet",
                   "The font is not in the file, so other computers show a different font.",
                   "Die Schrift ist nicht in der Datei; andere Computer zeigen eine andere Schrift."),
    "7.21.4.1-2": ("Letters missing from a font", "Buchstaben fehlen in einer Schrift",
                   "Some characters cannot be shown because the embedded font lacks them.",
                   "Einige Zeichen können nicht angezeigt werden, weil sie in der eingebetteten Schrift fehlen."),
    "7.21.4.2-1": ("Font character list wrong", "Zeichenliste der Schrift falsch",
                   "A font's list of included characters is wrong.", "Die Liste der enthaltenen Zeichen einer Schrift ist falsch."),
    "7.21.4.2-2": ("Font character list wrong", "Zeichenliste der Schrift falsch",
                   "A font's list of included characters is wrong.", "Die Liste der enthaltenen Zeichen einer Schrift ist falsch."),
    "7.21.5-1": ("Letter widths contradict the font", "Buchstabenbreiten widersprechen der Schrift",
                 "The widths in the file differ from those in the font.",
                 "Die Breiten in der Datei weichen von denen in der Schrift ab."),
    "7.21.6-1": ("Font character table missing", "Zeichentabelle der Schrift fehlt",
                 "A font cannot connect characters to their shapes in the standard way.",
                 "Eine Schrift kann Zeichen nicht auf die übliche Weise ihren Formen zuordnen."),
    "7.21.6-2": ("Font encoding not allowed", "Zeichenkodierung der Schrift nicht erlaubt",
                 "A font uses a character encoding that is not allowed.", "Eine Schrift verwendet eine nicht erlaubte Zeichenkodierung."),
    "7.21.6-3": ("Symbol font has an encoding", "Symbolschrift hat eine Kodierung",
                 "A symbol font has an encoding entry that it must not have.",
                 "Eine Symbolschrift hat einen Kodierungseintrag, den sie nicht haben darf."),
    "7.21.6-4": ("Symbol font character table wrong", "Zeichentabelle der Symbolschrift falsch",
                 "A symbol font lacks the character table that the standard expects.",
                 "Einer Symbolschrift fehlt die Zeichentabelle, die der Standard erwartet."),
    "7.21.7-1": ("Characters without meaning", "Zeichen ohne Bedeutung",
                 "Some characters cannot be turned into text, so screen readers read nothing or nonsense.",
                 "Einige Zeichen lassen sich nicht in Text umwandeln; Screenreader lesen nichts oder Unsinn."),
    "7.21.7-2": ("Characters with an invalid meaning", "Zeichen mit ungültiger Bedeutung",
                 "Some characters are linked to invalid text values.", "Einige Zeichen sind mit ungültigen Textwerten verbunden."),
    "7.21.8-1": ("Empty character used", "Leeres Zeichen verwendet",
                 "The text uses a placeholder character that shows nothing (often a tab or line break).",
                 "Der Text verwendet ein Platzhalterzeichen, das nichts anzeigt (oft ein Tabulator oder Zeilenumbruch)."),
}

_DEFAULT_TODO = (
    "Fix it in the program that made the PDF (for example Word: use 'Save as PDF' with the "
    "accessibility option), or with a PDF editor such as Adobe Acrobat Pro.",
    "Beheben Sie es im Programm, mit dem die PDF erstellt wurde (z. B. Word: 'Als PDF speichern' "
    "mit der Barrierefreiheits-Option), oder mit einem PDF-Editor wie Adobe Acrobat Pro.",
)

# What the author can do, for problems that often stay open: (EN, DE)
TODO: dict[str, tuple[str, str]] = {
    "7.1-11": ("Make the PDF again with tags switched on (in Word: 'Save as PDF', options, 'Document structure "
               "tags for accessibility').",
               "Erstellen Sie die PDF neu mit eingeschalteten Tags (in Word: 'Als PDF speichern', Optionen, "
               "'Dokumentstrukturtags für Barrierefreiheit')."),
    "7.16-1": ("Run the tool again with the owner password, or ask the author to allow 'content copying for "
               "accessibility' in the security settings.",
               "Starten Sie das Werkzeug erneut mit dem Besitzerkennwort, oder bitten Sie den Autor, in den "
               "Sicherheitseinstellungen 'Kopieren von Inhalten für Barrierefreiheit' zu erlauben."),
    "7.3-1": ("Check the descriptions the tool wrote, or add your own in the program that made the PDF.",
              "Prüfen Sie die Beschreibungen des Werkzeugs, oder fügen Sie eigene im Ursprungsprogramm hinzu."),
    "7.21.4.1-1": ("Embed all fonts when making the PDF (in Word: options, 'Embed fonts in the file').",
                   "Betten Sie beim Erstellen alle Schriften ein (in Word: Optionen, 'Schriftarten in der Datei einbetten')."),
    "7.21.7-1": ("Use common fonts, or set up an AI model so the tool can identify the characters.",
                 "Verwenden Sie gängige Schriften, oder richten Sie ein KI-Modell ein, damit das Werkzeug die Zeichen erkennt."),
    "7.21.8-1": ("Remove tabs and line breaks that were typed inside text boxes, then make the PDF again.",
                 "Entfernen Sie Tabulatoren und Zeilenumbrüche in Textfeldern und erstellen Sie die PDF neu."),
    "7.15-1": ("Convert the dynamic form to a static PDF form (e.g. in Adobe LiveCycle or Acrobat).",
               "Wandeln Sie das dynamische Formular in ein statisches PDF-Formular um (z. B. in Acrobat)."),
}


def problem_name(rule_id: str, language: str = "en", fallback: str | None = None) -> str:
    entry = PROBLEMS.get(rule_id)
    if entry is None:
        return fallback or rule_id
    return entry[1] if language == "de" else entry[0]


def problem_meaning(rule_id: str, language: str = "en", fallback: str | None = None) -> str:
    entry = PROBLEMS.get(rule_id)
    if entry is None:
        return fallback or ""
    return entry[3] if language == "de" else entry[2]


def problem_todo(rule_id: str, language: str = "en") -> str:
    entry = TODO.get(rule_id, _DEFAULT_TODO)
    return entry[1] if language == "de" else entry[0]


def rule_id_of(violation_name: str) -> str | None:
    """The veraPDF rule id of an internal violation name ('unsupported-7.2-30' -> '7.2-30')."""
    if violation_name.startswith("unsupported-"):
        return violation_name[len("unsupported-"):]
    return _rule_ids_by_name().get(violation_name)


_RULE_IDS: dict[str, str] | None = None


def _rule_ids_by_name() -> dict[str, str]:
    global _RULE_IDS
    if _RULE_IDS is None:
        from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.taxonomy_data_mapping.map_verapdf_violation_to_taxonomy_data import (
            map_rule_id_to_syntax_violation_name,
        )
        _RULE_IDS = {}
        for rule_id in PROBLEMS:
            try:
                _RULE_IDS[map_rule_id_to_syntax_violation_name(rule_id)] = rule_id
            except Exception:
                continue
    return _RULE_IDS


def plain_name(violation_name: str, language: str = "en") -> str:
    rule_id = rule_id_of(violation_name)
    return problem_name(rule_id, language, fallback=violation_name) if rule_id else violation_name
