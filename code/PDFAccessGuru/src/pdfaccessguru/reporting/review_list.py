"""
Optional review list: values PDFAccessGuru wrote automatically, grouped so that a person
can check them in a few minutes instead of going through hundreds of single entries.

Design rules
- Grouped by kind (image descriptions, document title, ...), each group explains in plain
  language why it matters and how to check it.
- The check never depends on seeing the page: every group says what to compare the value
  with (caption, nearby text, link target), so blind and low-vision users can do it too,
  and it says when asking a sighted colleague is the better option.
- Identical values (e.g. the same logo description on every page) are shown once.
- "Check first" groups come before "Spot-check" groups; long groups show a few examples.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

SECONDS_PER_ITEM = 30
EXAMPLES_PER_GROUP = 5


@dataclass(frozen=True)
class ReviewGroupInfo:
    title: str
    why: str
    how_to_check: str
    check_first: bool


_GROUPS: dict[str, ReviewGroupInfo] = {
    "title": ReviewGroupInfo(
        "Title of the file",
        "A screen reader says the title when the file opens.",
        "Is this the right title? If not, change it in the file properties.",
        True,
    ),
    "language": ReviewGroupInfo(
        "Language of the file",
        "A screen reader uses it to pick the right voice.",
        "Is this the main language of the file?",
        True,
    ),
    "images": ReviewGroupInfo(
        "Descriptions of pictures",
        "A screen reader reads this text instead of showing the picture.",
        "Does the text describe the picture? If you cannot see the picture, compare the text with the caption "
        "shown below it, or ask a colleague to look.",
        True,
    ),
    "formulas": ReviewGroupInfo(
        "Descriptions of formulas",
        "A screen reader reads this text instead of the formula.",
        "Does the text say the formula correctly? If you cannot see the formula, compare it with the text "
        "shown below it, or ask a colleague.",
        True,
    ),
    "media": ReviewGroupInfo(
        "Descriptions of videos and sounds",
        "A screen reader reads this text instead of playing the video or sound.",
        "Does the text say what the video or sound is about?",
        True,
    ),
    "characters": ReviewGroupInfo(
        "Special characters",
        "Some symbols may be read out wrong.",
        "Copy the text on these pages into a text editor. Do symbols like Greek letters and math signs look right?",
        True,
    ),
    "links": ReviewGroupInfo(
        "Descriptions of links",
        "A screen reader reads this text for a link.",
        "Look at 2 or 3: does the text say where the link goes?",
        False,
    ),
    "structure": ReviewGroupInfo(
        "Headings and tables",
        "People who use screen readers jump from heading to heading and read tables cell by cell.",
        "Look at 2 or 3 in the tags panel of your PDF program.",
        False,
    ),
    "forms": ReviewGroupInfo(
        "Descriptions of form fields",
        "A screen reader reads this text when you are in the field.",
        "Does the text say what to type in the field?",
        False,
    ),
    "other": ReviewGroupInfo(
        "Other names",
        "Names of layers and attached files.",
        "Change them only if they are wrong.",
        False,
    ),
}

# German titles and explanations of the groups (Phase 7a): key -> (title, why, how)
_GROUPS_DE: dict[str, tuple[str, str, str]] = {
    "title": ("Titel der Datei", "Ein Screenreader sagt den Titel, wenn die Datei geöffnet wird.",
              "Ist das der richtige Titel? Wenn nicht, ändern Sie ihn in den Dateieigenschaften."),
    "language": ("Sprache der Datei", "Ein Screenreader wählt damit die richtige Stimme.",
                 "Ist das die Hauptsprache der Datei?"),
    "images": ("Bildbeschreibungen", "Ein Screenreader liest diesen Text, statt das Bild zu zeigen.",
               "Beschreibt der Text das Bild? Wenn Sie das Bild nicht sehen, vergleichen Sie den Text mit der "
               "Bildunterschrift darunter oder bitten Sie eine Kollegin oder einen Kollegen, nachzusehen."),
    "formulas": ("Formelbeschreibungen", "Ein Screenreader liest diesen Text statt der Formel.",
                 "Gibt der Text die Formel richtig wieder? Wenn Sie die Formel nicht sehen, vergleichen Sie sie "
                 "mit dem Text darunter."),
    "media": ("Beschreibungen von Videos und Tönen", "Ein Screenreader liest diesen Text, statt das Video oder den Ton abzuspielen.",
              "Sagt der Text, worum es in dem Video oder Ton geht?"),
    "characters": ("Sonderzeichen", "Einige Symbole werden womöglich falsch vorgelesen.",
                   "Kopieren Sie den Text dieser Seiten in einen Texteditor. Sehen Symbole wie griechische "
                   "Buchstaben und mathematische Zeichen richtig aus?"),
    "links": ("Linkbeschreibungen", "Ein Screenreader liest diesen Text für einen Link.",
              "Sehen Sie sich 2 oder 3 an: Sagt der Text, wohin der Link führt?"),
    "structure": ("Überschriften und Tabellen", "Screenreader-Nutzer springen von Überschrift zu Überschrift und "
                  "lesen Tabellen Zelle für Zelle.", "Sehen Sie sich 2 oder 3 im Tag-Bereich Ihres PDF-Programms an."),
    "forms": ("Beschreibungen von Formularfeldern", "Ein Screenreader liest diesen Text, wenn man im Feld ist.",
              "Sagt der Text, was in das Feld einzutragen ist?"),
    "other": ("Andere Namen", "Namen von Ebenen und angehängten Dateien.", "Ändern Sie sie nur, wenn sie falsch sind."),
}

_GROUP_BY_VIOLATION = {
    "missing-metadata-stream-dc-title": "title",
    "natural-language-undefined": "language",
    "invalid-lang-entry": "language",
    "figure-structure-alternate-description-missing": "images",
    "formula-structure-no-alternative-description": "formulas",
    "alt-missing-media-clip-data": "media",
    "glyph-cannot-mapped-unicode": "characters",
    "glyph-invalid-unicode": "characters",
    "link-annotation-missing-alternate-description-contents": "links",
    "document-uses-h-h#-tags": "structure",
    "document-uses-hn-h-tags": "structure",
    "table-several-captions": "structure",
    "table-columns-different-number-rows": "structure",
    "table-rows-span-different-number-columns": "structure",
    "table-rows-span-different-number-columns-02": "structure",
    "form-field-missing-alt-entry": "forms",
}


def _group_key(violation_name: str) -> str:
    if violation_name in _GROUP_BY_VIOLATION:
        return _GROUP_BY_VIOLATION[violation_name]
    if violation_name.startswith("natural-language"):
        return "language"
    return "other"


_QUOTED_VALUE = re.compile(r"'(.+)'")


def _shown_value(message: str) -> str:
    """The written value if the message quotes it, otherwise the whole message."""
    match = _QUOTED_VALUE.search(message)
    return match.group(1) if match else message


@dataclass
class ReviewItem:
    value: str
    pages: list[int] = field(default_factory=list)
    occurrences: int = 0
    # Text to compare the value with (caption, nearby text) - needed by reviewers who cannot see the page.
    context: str | None = None
    # Picture of the element (base64 PNG) - shown to sighted reviewers next to the value.
    image_png_base64: str | None = None


@dataclass
class ReviewGroup:
    key: str
    info: ReviewGroupInfo
    items: list[ReviewItem] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(item.occurrences for item in self.items)


def build_review_groups(report: dict[str, Any]) -> list[ReviewGroup]:
    """Collect all REVIEW lines of the correction phases into deduplicated, ordered groups."""
    groups: dict[str, ReviewGroup] = {}
    for phase in report.get("phases", []):
        if phase.get("name") != "correction":
            continue
        for run in phase.get("corrections", []):
            for line in run.get("lines", []):
                if line.get("level") != "review":
                    continue
                key = _group_key(str(run.get("violation_name", "")))
                group = groups.setdefault(key, ReviewGroup(key, _GROUPS[key]))
                value = _shown_value(str(line.get("message", "")))
                item = next((existing for existing in group.items if existing.value == value), None)
                if item is None:
                    item = ReviewItem(value)
                    group.items.append(item)
                item.occurrences += 1
                item.context = item.context or line.get("context")
                item.image_png_base64 = item.image_png_base64 or line.get("image_png_base64")
                page = run.get("page") if isinstance(run.get("page"), int) else line.get("page")
                if isinstance(page, int) and page not in item.pages:
                    item.pages.append(page)
    order = list(_GROUPS)
    return sorted(groups.values(), key=lambda g: (not g.info.check_first, order.index(g.key)))


def estimated_minutes(groups: list[ReviewGroup]) -> int:
    """Rough time to go through the review list: check-first items fully, spot-check groups by sample."""
    items = sum(len(g.items) if g.info.check_first else min(len(g.items), EXAMPLES_PER_GROUP) for g in groups)
    return max(1, round(items * SECONDS_PER_ITEM / 60)) if items else 0


def _pages_text(pages: list[int], language: str = "en") -> str:
    page, many, unknown = ("Seite", "Seiten", "Seite unbekannt") if language == "de" else ("page", "pages", "page not known")
    if not pages:
        return unknown
    pages = sorted(pages)
    if len(pages) > 6:
        return f"{many} {pages[0]}–{pages[-1]} ({len(pages)} {many})"
    return (page if len(pages) == 1 else many) + " " + ", ".join(str(p) for p in pages)


def _shown_items(group: ReviewGroup) -> list[ReviewItem]:
    if group.info.check_first and len(group.items) <= 20:
        return group.items
    return group.items[:EXAMPLES_PER_GROUP]


def _image_path(group: ReviewGroup, index: int) -> str:
    return f"review_images/{group.key}_{index + 1}.png"


def review_list_images(groups: list[ReviewGroup]) -> dict[str, bytes]:
    """PNG files referenced by review_list_markdown, keyed by their relative path."""
    import base64

    images: dict[str, bytes] = {}
    for group in groups:
        for index, item in enumerate(_shown_items(group)):
            if item.image_png_base64:
                images[_image_path(group, index)] = base64.b64decode(item.image_png_base64)
    return images


def review_list_markdown(groups: list[ReviewGroup], include_pictures: bool = True, language: str = "en") -> list[str]:
    """
    Markdown lines for the list of things to check (pictures are referenced as relative files).
    Every entry shows the page, the text the tool wrote and, if known, a text to compare it with,
    so the list also works without pictures and for people who cannot see the page.
    """
    if not groups:
        return []
    de = language == "de"
    minutes = estimated_minutes(groups)
    if de:
        intro = [
            "## Zu prüfende Texte", "",
            f"Diese Texte hat das Werkzeug selbst geschrieben. Die Prüfung dauert etwa {minutes} Minute{'' if minutes == 1 else 'n'}.", "",
            "Beginnen Sie mit den Teilen „Bitte prüfen“. Bei den Teilen „Stichprobe“ reicht es, 2 oder 3 anzusehen.", "",
        ]
    else:
        intro = [
            "## Things to Check", "",
            f"The tool wrote these texts itself. Checking them takes about {minutes} minute{'' if minutes == 1 else 's'}.", "",
            "Start with the parts marked “Please check”. For the parts marked “Check a few”, looking at 2 or 3 is enough.", "",
        ]
    lines = intro
    for group in groups:
        title, why, how = _GROUPS_DE.get(group.key, (group.info.title, group.info.why, group.info.how_to_check)) if de \
            else (group.info.title, group.info.why, group.info.how_to_check)
        label = ("Bitte prüfen" if de else "Please check") if group.info.check_first else ("Stichprobe" if de else "Check a few")
        lines.extend([f"### {title} ({label})", "", f"{'Warum' if de else 'Why'}: {why}", "",
                      f"{'Wie' if de else 'How'}: {how}", ""])
        shown = _shown_items(group)
        for index, item in enumerate(shown):
            where = _pages_text(item.pages, language)
            where = where[0].upper() + where[1:]
            if include_pictures and item.image_png_base64:
                alt = (f"Bild von {where}. Der dafür geschriebene Text steht darunter." if de
                       else f"Picture from {where.lower()}. The text written for it is below.")
                lines.append(f"![{alt}]({_image_path(group, index)})")
                lines.append("")
            repeated = ((f" ({item.occurrences}-mal verwendet)" if de else f" (used {item.occurrences} times)")
                        if item.occurrences > 1 else "")
            wrote = "Das Werkzeug schrieb" if de else "The tool wrote"
            quote = f"„{item.value}“" if de else f"“{item.value}”"
            lines.append(f"- {where}. {wrote}: {quote}{repeated}")
            if item.context:
                compare = "Vergleichen Sie mit:" if de else "Compare with the"
                context = item.context if de else item.context[0].lower() + item.context[1:]
                if de:
                    for english, german in (("Caption: ", "Bildunterschrift: "), ("Nearby text: ", "Text in der Nähe: ")):
                        context = context.replace(english, german, 1)
                lines.append(f"  - {compare} {context}")
            lines.append("")
        if len(shown) < len(group.items):
            more = len(group.items) - len(shown)
            lines.append(f"- {more} weitere stehen im technischen Bericht." if de
                         else f"- {more} more are listed in the technical report.")
            lines.append("")
    return lines
