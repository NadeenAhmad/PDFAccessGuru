"""Phase 11: a link written as several pieces gets one description from all its text."""

from __future__ import annotations

import pymupdf as fitz
import pikepdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.links import describe_links


def test_a_link_split_into_words_is_described_with_its_whole_text(tmp_path):
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_text((72, 100), "A short introduction is available from the PDF Association today.", fontsize=11)
    page.insert_text((72, 140), "Another link: example page.", fontsize=11)
    uri = "https://pdfa.org/resource/pdfua-in-a-nutshell/"
    for word in ("PDF", "Association"):                     # one link per word, as some programs write them
        area = page.search_for(word)[-1] if word == "PDF" else page.search_for(word)[0]
        page.insert_link({"kind": fitz.LINK_URI, "from": area, "uri": uri})
    page.insert_link({"kind": fitz.LINK_URI, "from": page.search_for("example page")[0], "uri": "https://example.org"})
    document.save(tmp_path / "in.pdf")
    with pikepdf.open(tmp_path / "in.pdf") as pdf:
        describe_links(pdf)
        texts = [str(a.Contents) for a in pdf.pages[0].Annots]
    assert texts[0] == texts[1] == "PDF Association (link to pdfa.org/resource/pdfua-in-a-nutshell)"
    assert texts[2] == "example page (link to example.org)"
