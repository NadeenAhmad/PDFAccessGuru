"""Phase 7b: checking and changing the texts the tool wrote, and the screen reader preview."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode

import fitz
import pikepdf
import pytest

from pdfaccessguru.tagging.builder import tag_document
from pdfaccessguru.webapp.preview import preview_html
from pdfaccessguru.webapp.review import EditError, apply, collect, version
from test.webapp_test import RESOURCES, _request, _upload, _wait, app  # noqa: F401  (fixture)


def _pdfs(tmp_path: Path) -> tuple[Path, Path]:
    """An original without descriptions, and a 'fixed' copy with tags and texts like the tool writes."""
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 90), "Results", fontsize=18, fontname="hebo")
    page.insert_text((72, 130), "The picture below shows the network, see the project page.", fontsize=11)
    page.insert_link({"kind": fitz.LINK_URI, "from": page.search_for("project page")[0], "uri": "https://example.org"})
    picture = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 30), False)
    picture.clear_with(120)
    page.insert_image(fitz.Rect(72, 160, 272, 310), pixmap=picture)
    page.insert_text((72, 330), "Figure 1: The network", fontsize=10)
    original = tmp_path / "original.pdf"
    document.save(original)
    fixed = tmp_path / "fixed.pdf"
    with pikepdf.open(original) as pdf:
        tag_document(pdf)
        root = pdf.Root.StructTreeRoot
        figure = next(kid for kid in root.K[0].K if kid.S == "/Figure")
        figure.Alt = pikepdf.String("Picture")
        pdf.pages[0].obj.Annots[0].Contents = pikepdf.String("Link to example.org")
        pdf.Root.Lang = pikepdf.String("en")
        pdf.docinfo["/Title"] = "Results"
        pdf.save(fixed)
    return original, fixed


def test_texts_written_by_the_tool_are_listed_with_something_to_compare_with(tmp_path):
    original, fixed = _pdfs(tmp_path)
    entries = {entry.group: entry for entry in collect(fixed, original)}
    assert entries["document"].key in ("title", "lang")
    picture = entries["pictures"]
    assert picture.text == "Picture" and picture.page == 1 and picture.has_picture
    assert picture.context == "Caption: Figure 1: The network" or "Figure 1" in picture.context
    link = entries["links"]
    assert link.text == "Link to example.org" and "example.org" in link.context and "project page" in link.context


def test_changes_go_into_the_pdf_and_bad_ones_are_refused(tmp_path):
    original, fixed = _pdfs(tmp_path)
    entries = {entry.group: entry for entry in collect(fixed, original)}
    before = version(fixed)
    assert apply(fixed, {entries["pictures"].key: "Diagram of the network with three servers",
                         "title": "Results of the study", "lang": "en-GB"}) == 3
    assert version(fixed) != before
    with pikepdf.open(fixed) as pdf:
        assert str(pdf.Root.Lang) == "en-GB" and str(pdf.docinfo.Title) == "Results of the study"
    texts = [entry.text for entry in collect(fixed, original)]
    assert "Diagram of the network with three servers" in texts
    unchanged = version(fixed)
    with pytest.raises(EditError):
        apply(fixed, {entries["links"].key: "   "})
    with pytest.raises(EditError):
        apply(fixed, {"lang": "English please"})
    assert version(fixed) == unchanged                                  # nothing written


def test_the_preview_reads_like_a_screen_reader(tmp_path):
    _, fixed = _pdfs(tmp_path)
    preview = preview_html(fixed, "en")
    assert "<strong>Title:</strong> Results" in preview
    assert re.search(r"<h2><span lang=\"en\">Results</span></h2>", preview)
    assert "[Picture: Picture]" in preview and "The picture below shows the network" in preview
    assert preview.index("Results</span></h2>") < preview.index("[Picture:") < preview.index("Figure 1")


def test_the_app_lets_people_check_change_and_preview(app):  # noqa: F811
    pdf = (RESOURCES / "veraPDF_corpus/7.3-t01-fail-a.pdf").read_bytes()
    status, headers = _upload(app, pdf, language_ui="en", review="on")
    job_path = headers["Location"]
    assert _wait(app, job_path)["state"] == "done"
    page = _request(app, "GET", job_path)[2].decode()
    to_review_before = _to_review(page)
    check = re.search(r'href="([^"]+/check/1)"', page).group(1)
    preview = re.search(r'href="([^"]+/preview/1)"', page).group(1)

    form = _request(app, "GET", check)[2].decode()
    assert form.count("<h1>") == 1
    fields = set(re.findall(r'<(?:textarea|input type="text")[^>]*\bid="([^"]+)"', form))
    assert "title" in fields and "lang" in fields and set(re.findall(r'<label for="([^"]+)"', form)) >= fields
    picture_key = next(key for key in fields if key.endswith("-Alt"))
    values = {"version": re.search(r'name="version" value="([^"]+)"', form).group(1), "accept": "pictures",
              "title": "Test page", "lang": "en", picture_key: "Company logo"}
    body = urlencode(values).encode()
    saved = _request(app, "POST", check, body, {"Content-Type": "application/x-www-form-urlencoded"})[2].decode()
    assert "Saved. The new PDF and the report now include your changes." in saved
    assert "Picture descriptions (1) – reviewed" in saved and "Company logo" in saved
    assert "still shows the texts as the tool wrote them" not in saved

    # Phase 12c: the report now says what the user changed and reviewed, and less is left to review
    page = _request(app, "GET", job_path)[2].decode()
    report_link = re.search(r'href="([^"]+_report\.md)"', page).group(1)
    report = _request(app, "GET", report_link)[2].decode()
    assert "## Your Changes" in report and "- Picture descriptions: reviewed by you" in report
    assert re.search(r"- Picture description on page 1: changed by you to “Company logo” \(the tool wrote “.+”\)", report)
    assert "- Title: changed by you to “Test page”" in report
    assert "(reviewed by you)" in report and "Changed by you to: “Company logo”" in report
    assert _to_review(page) < to_review_before
    again = _request(app, "POST", check, body, {"Content-Type": "application/x-www-form-urlencoded"})[2].decode()
    assert 'role="alert"' in again and "changed in the meantime" in again        # an old form is not applied

    shown = _request(app, "GET", preview)[2].decode()
    assert shown.count("<h1>") == 1 and "[Picture: Company logo]" in shown


def _to_review(page: str) -> int:
    return int(re.search(r"Texts to review</dt>\s*<dd>(\d+)</dd>", page).group(1))


def _logo_pdf(path: Path) -> Path:
    """Three pages with a picture in the page header (looks like a logo, so it becomes decoration)."""
    document = fitz.open()
    logo = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 60, 30), False)
    logo.clear_with(90)
    for number in range(1, 4):
        page = document.new_page(width=595, height=842)
        page.insert_image(fitz.Rect(480, 20, 560, 60), pixmap=logo)
        page.insert_text((72, 40), "Institute of Examples", fontsize=9)
        page.insert_text((72, 120), f"Chapter {number}", fontsize=18, fontname="hebo")
        page.insert_text((72, 160), "This page explains one part of the topic in a few plain sentences.", fontsize=11)
        page.insert_text((290, 815), str(number), fontsize=9)
    document.save(path)
    return path


def test_pictures_hidden_as_decoration_can_be_shown_with_a_description(tmp_path):
    from collections import Counter

    from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
    from pdfaccessguru.webapp.review import hidden_pictures, hidden_text

    fixed = tmp_path / "fixed.pdf"
    with pikepdf.open(_logo_pdf(tmp_path / "original.pdf")) as pdf:
        tag_document(pdf)
        pdf.Root.Lang = pikepdf.String("en")              # as the pipeline sets it
        pdf.save(fixed)
    pictures = hidden_pictures(fixed)
    assert len(pictures) == 1 and pictures[0].pages == [1, 2, 3]
    assert any("Institute of Examples" in text and count == 3 for text, count in hidden_text(fixed))
    with pytest.raises(EditError):
        apply(fixed, {}, {pictures[0].key: "  "})
    assert apply(fixed, {}, {pictures[0].key: "Logo of the Institute of Examples"}) == 3
    assert hidden_pictures(fixed) == []
    with pikepdf.open(fixed) as pdf:
        figures = [kid for kid in pdf.Root.StructTreeRoot.K[0].K if kid.get("/S") == "/Figure"]
        assert len(figures) == 3 and all(str(f.Alt) == "Logo of the Institute of Examples" for f in figures)
    assert "[Picture: Logo of the Institute of Examples]" in preview_html(fixed, "en")
    rules = Counter(v.rule_id for v in run_verapdf(str(fixed)))
    # tags, decoration and picture descriptions are all right (title and metadata are set by the pipeline)
    assert not [rule for rule in rules if rule.startswith(("7.1-", "7.2-", "7.3-")) and rule not in ("7.1-8", "7.1-10")], rules


def test_a_text_changed_twice_keeps_the_tools_text_and_a_change_back_is_dropped():
    from pdfaccessguru.webapp.review import Entry
    from pdfaccessguru.webapp.server import _remember_review

    report: dict = {}
    first = Entry("5-0-Alt", "pictures", "Picture", page=2)
    assert _remember_review(report, {first.key: first}, {first.key: "Logo"}, {}, "")
    second = Entry("7-0-Alt", "pictures", "Logo", page=2)            # keys change when the file is saved
    _remember_review(report, {second.key: second}, {second.key: "University logo"}, {}, "")
    assert report["user_review"]["changes"] == [{"group": "images", "page": 2, "old": "Picture", "new": "University logo"}]
    third = Entry("9-0-Alt", "pictures", "University logo", page=2)
    _remember_review(report, {third.key: third}, {third.key: "Picture"}, {}, "")
    assert report["user_review"]["changes"] == []
    unchanged = Entry("9-0-Alt", "pictures", "Picture", page=2)
    assert not _remember_review(report, {unchanged.key: unchanged}, {unchanged.key: " Picture "}, {}, "")
    assert _remember_review(report, {}, {}, {"3-0": "A logo"}, "pictures")
    assert report["user_review"]["shown"] == 1 and report["user_review"]["reviewed"] == ["images"]
