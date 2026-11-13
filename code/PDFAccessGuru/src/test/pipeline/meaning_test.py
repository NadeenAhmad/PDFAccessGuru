"""Phase 10: meaning and structure beyond the automatic check: exact fixes, the rest listed."""

from __future__ import annotations

import pymupdf as fitz
import pikepdf

from pdfaccessguru.pipeline.meaning import MeaningResult, check_meaning, clear_empty_descriptions
from pdfaccessguru.tagging.builder import tag_document

ENGLISH = ("The survey shows clearly that the method works for most documents in the collection.",
           "It was tested on many files from different sources and programs during the last year.")
GERMAN = ("Die Umfrage zeigt deutlich, dass die Methode für die meisten Dokumente der Sammlung gut "
          "funktioniert und von vielen Menschen genutzt wird.")


def _tagged(path, pages=1, german=False, link_text=None, bullets=False):
    document = fitz.open()
    for number in range(pages):
        page = document.new_page(width=595, height=842)
        page.insert_text((72, 90), f"{number + 1} Results", fontsize=18, fontname="hebo")
        y = 130
        for line in ENGLISH:
            page.insert_text((72, y), line, fontsize=10)
            y += 14
        if german and number == 0:
            y += 20
            words, line = GERMAN.split(), ""
            for word in words:
                if len(line) + len(word) > 85:
                    page.insert_text((72, y), line, fontsize=10)
                    y += 14
                    line = ""
                line = (line + " " + word).strip()
            page.insert_text((72, y), line, fontsize=10)
        if link_text and number == 0:
            page.insert_text((72, 300), f"For details {link_text}.", fontsize=10)
            area = page.search_for(link_text)[0]
            page.insert_link({"kind": fitz.LINK_URI, "from": area, "uri": "https://example.org/report"})
        if bullets and number == 0:
            page.insert_text((90, 340), "• First point of the list", fontsize=10)
            page.insert_text((90, 354), "• Second point of the list", fontsize=10)
        picture = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 30), False)
        picture.clear_with(150)
        page.insert_image(fitz.Rect(72, 400, 272, 550), pixmap=picture)
    document.save(path)
    pdf = pikepdf.open(path, allow_overwriting_input=True)
    tag_document(pdf)
    pdf.Root.Lang = pikepdf.String("en")
    return pdf


def _elements(pdf, kind):
    found = []

    def walk(element):
        value = element.get("/K")
        for kid in (list(value) if isinstance(value, pikepdf.Array) else [value] if value is not None else []):
            if isinstance(kid, pikepdf.Dictionary) and "/S" in kid:
                if kid.S == kind:
                    found.append(kid)
                walk(kid)

    walk(pdf.Root.StructTreeRoot)
    return found


def test_descriptions_that_say_nothing_are_cleared_and_image_of_is_removed(tmp_path):
    pdf = _tagged(tmp_path / "a.pdf")
    figure = _elements(pdf, "/Figure")[0]
    result = MeaningResult()
    for alt, expected in (("IMG_2041.jpg", None), ("Bild", None), ("image", None),
                          ("Image of a red house by the sea", "A red house by the sea"),
                          ("Bild von einem roten Haus", "Einem roten Haus"),
                          ("Diagram of the network", "Diagram of the network")):
        figure.Alt = pikepdf.String(alt)
        clear_empty_descriptions(pdf, result)
        assert (str(figure.Alt) if "/Alt" in figure else None) == expected, alt
    assert result.alt_cleared == 3 and result.alt_prefix == 2


def test_a_passage_in_another_language_gets_its_language(tmp_path):
    pdf = _tagged(tmp_path / "a.pdf", german=True)
    result = MeaningResult()
    check_meaning(pdf, result)
    languages = {str(p.get("/Lang", "")) for p in _elements(pdf, "/P")}
    assert result.language_parts == 1 and result.languages == {"de": 1} and languages == {"", "de"}


def test_table_header_cells_get_their_direction(tmp_path):
    from test.pipeline.tagging_test import _table_pdf

    with pikepdf.open(_table_pdf(tmp_path / "t.pdf")) as pdf:
        tag_document(pdf)
        pdf.Root.Lang = pikepdf.String("en")
        headers = _elements(pdf, "/TH")
        for cell in headers:
            del cell["/A"]                                     # as many authoring tools write them
        rows = _elements(pdf, "/TR")
        first_cell = rows[1].K[0]
        first_cell.S = pikepdf.Name.TH                          # a row header without a direction
        result = MeaningResult()
        check_meaning(pdf, result)
        assert all(str(cell.A.Scope) == "/Column" for cell in headers)
        assert str(first_cell.A.Scope) == "/Row" and result.table_scope == len(headers) + 1


def test_things_to_check_are_listed(tmp_path):
    pdf = _tagged(tmp_path / "a.pdf", pages=3, link_text="click here", bullets=True)
    # no headings in this copy, the bullets as plain paragraphs, a long picture description
    for heading in _elements(pdf, "/H1"):
        heading.S = pikepdf.Name.P
    document = pdf.Root.StructTreeRoot.K[0]
    kids = list(document.K)
    for index, kid in enumerate(kids):
        if kid.S == "/L":
            paragraphs = []
            for item in kid.K:
                body = item.K[0] if isinstance(item.K, pikepdf.Array) else item.K
                body.S, body.P = pikepdf.Name.P, document
                paragraphs.append(body)
            kids[index:index + 1] = paragraphs
            break
    document.K = pikepdf.Array(kids)
    # longer than the limit of the chosen level (1.1: standard = 600 characters)
    _elements(pdf, "/Figure")[0].Alt = pikepdf.String("A very long description " * 30)
    result = MeaningResult()
    check_meaning(pdf, result)
    assert result.no_headings and [text for _, text in result.vague_links] == ["click here"]
    assert len(result.list_like) == 1 and len(result.long_alt) == 1


def test_the_report_says_what_was_fixed_and_what_to_check():
    from pdfaccessguru.reporting.customer_report import _meaning_section

    meaning = {"alt_cleared": 2, "alt_prefix": 0, "language_parts": 1, "languages": {"de": 1}, "table_scope": 3,
               "vague_links": [(4, "click here")], "vague_links_count": 1, "long_alt": [], "long_alt_count": 0,
               "long_headings": [], "long_headings_count": 0, "no_headings": False, "list_like": [],
               "list_like_count": 0, "tiny_figures": 0, "tables_without_headers": 1}
    text = "\n".join(_meaning_section(meaning, "en"))
    assert "## Meaning and Structure" in text and "Fixed:" in text and "Please review:" in text
    assert "(de: 1)" in text and "on page 4" in text and "Tables without header cells: 1." in text
    assert "Bedeutung und Struktur" in "\n".join(_meaning_section(meaning, "de"))


def test_web_addresses_in_the_text_become_real_links(tmp_path):
    from collections import Counter

    from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf

    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 90), "Further reading", fontsize=18, fontname="hebo")
    page.insert_text((72, 130), "The course page is www.example.org/course for all slides.", fontsize=11)
    page.insert_text((72, 146), "Already a link: https://example.org/linked here.", fontsize=11)
    page.insert_link({"kind": fitz.LINK_URI, "from": page.search_for("https://example.org/linked")[0],
                      "uri": "https://example.org/linked"})
    document.save(tmp_path / "in.pdf")
    with pikepdf.open(tmp_path / "in.pdf") as pdf:
        tag_document(pdf)
        pdf.Root.Lang = pikepdf.String("en")
        pdf.save(tmp_path / "tagged.pdf")
        result = MeaningResult()
        check_meaning(pdf, result)
        pdf.save(tmp_path / "out.pdf")
    assert result.links_made == 1
    with fitz.open(tmp_path / "out.pdf") as out:
        uris = sorted(link["uri"] for link in out[0].get_links())
    assert uris == ["https://example.org/linked", "https://www.example.org/course"]
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        links = _elements(pdf, "/Link")
        new = next(link for link in links if "course" in str(link.K[0].Obj.A.URI))
        assert str(new.P.S) == "/P" and str(new.K[0].Obj.Contents) == "Link to example.org/course"
    before = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "tagged.pdf")))
    after = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert not after - before, after - before              # the new link brings no new problem


def test_a_wrong_document_language_is_corrected_by_the_majority(tmp_path):
    """An English text marked as German (e.g. from a German title page): the document becomes
    English, and only the German passage keeps German."""
    pdf = _tagged(tmp_path / "a.pdf", pages=4, german=True)
    pdf.Root.Lang = pikepdf.String("de")
    result = MeaningResult()
    check_meaning(pdf, result)
    assert str(pdf.Root.Lang) == "en" and result.document_language == ("de", "en")
    assert result.languages == {"de": 1}


def test_a_web_address_in_a_list_item_gets_its_link_in_the_item_body(tmp_path):
    """A Link directly inside an LI would break rule 7.2-20 (found on a real thesis)."""
    from collections import Counter

    from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf

    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 90), "Sources", fontsize=18, fontname="hebo")
    page.insert_text((90, 130), "• The project page www.example.org/project for details", fontsize=11)
    page.insert_text((90, 146), "• The second source of this work", fontsize=11)
    document.save(tmp_path / "in.pdf")
    with pikepdf.open(tmp_path / "in.pdf") as pdf:
        tag_document(pdf)
        pdf.Root.Lang = pikepdf.String("en")
        pdf.save(tmp_path / "tagged.pdf")
        result = MeaningResult()
        check_meaning(pdf, result)
        pdf.save(tmp_path / "out.pdf")
    assert result.links_made == 1
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        assert [str(link.P.S) for link in _elements(pdf, "/Link")] == ["/LBody"]
    before = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "tagged.pdf")))
    after = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert after["7.2-20"] == 0 and not after - before
