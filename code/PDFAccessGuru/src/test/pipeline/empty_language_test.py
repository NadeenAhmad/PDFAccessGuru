"""
1.1.6: structure elements with an empty language (/Lang "", rule 7.2-29), as PowerPoint writes them for
every Span. veraPDF points at the Lang value itself ("…/K[0](… SESpan Span)/Lang[0]"); the fix must
reach the Span that holds it, not the document catalog (which already had a language, so nothing changed).
"""

from __future__ import annotations

from collections import Counter

import pikepdf
from pikepdf import Name, String

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_4_riard_qupevaj import (
    correct_invalid_lang_entry,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.map_violation.detect_affected_element.detect_affected_element import (
    detect_affected_element,
)
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
from pdfaccessguru.pipeline.pipeline import run_pipeline
from test.pipeline.structure_repair_test import build


def _deck(path):
    """A slide: an English heading and a German paragraph, every Span with Lang "" (as PowerPoint writes it)."""
    pdf = build(("Document", [
        ("H1", [("Span", "Quarterly results", (72, 700)), ("Span", "and next steps", (72, 680))]),
        ("P", [("Span", "Die Ergebnisse sind gut und wir machen weiter so.", (72, 640))]),
    ]))
    pdf.Root["/Lang"] = String("en")
    for element in pdf.objects:
        if isinstance(element, pikepdf.Dictionary) and element.get("/S") == Name.P:
            element["/Lang"] = String("de")
        if isinstance(element, pikepdf.Dictionary) and element.get("/S") == Name.Span:
            element["/Lang"] = String("")
    pdf.save(path)
    return path


def _span_languages(path) -> list[str]:
    with pikepdf.open(path) as pdf:
        return sorted(str(o.get("/Lang")) for o in pdf.objects
                      if isinstance(o, pikepdf.Dictionary) and o.get("/S") == Name.Span)


def test_the_span_that_holds_an_empty_language_gets_the_language_around_it(tmp_path):
    source = _deck(tmp_path / "deck.pdf")
    found = [v for v in run_verapdf(str(source)) if v.rule_id == "7.2-29"]
    assert len(found) == 3 and all(v.context.endswith("Span)/Lang[0]") for v in found)

    from pdfaccessguru.model.detected_violation import DetectedViolation
    from pdfaccessguru.model.violation import Violation
    from pdfaccessguru.model.violation_category import ViolationCategory

    violation = Violation(category=ViolationCategory.SYNTAX, name="invalid-lang-entry", description="", guidelines=[])
    with pikepdf.open(source) as pdf:
        for verapdf_violation in found:
            element = detect_affected_element(verapdf_violation, pdf)
            assert isinstance(element, pikepdf.Dictionary) and element.get("/S") == Name.Span
            correct_invalid_lang_entry(DetectedViolation(violation=violation, affected_element=element,
                                                         supplementary_information=[]), pdf)
        assert str(pdf.Root.Lang) == "en"                         # the document language is left alone
        pdf.save(tmp_path / "fixed.pdf")

    assert _span_languages(tmp_path / "fixed.pdf") == ["de", "en", "en"]   # nearest parent, else the document
    assert not [v for v in run_verapdf(str(tmp_path / "fixed.pdf")) if v.rule_id == "7.2-29"]


def test_the_pipeline_keeps_these_fixes(tmp_path):
    source = _deck(tmp_path / "deck.pdf")
    report = run_pipeline(str(source), str(tmp_path / "out.pdf"))

    after = Counter(v.rule_id for v in run_verapdf(str(tmp_path / "out.pdf")))
    assert after["7.2-29"] == 0
    assert "" not in _span_languages(tmp_path / "out.pdf")
    messages = [line["message"] for phase in report["phases"] for line in phase["lines"]]
    assert any("7.2-29: 3 problem(s) disappeared" in message for message in messages)


def test_a_marked_content_number_before_the_span_does_not_shift_the_count(tmp_path):
    """veraPDF counts only structure elements in K[n]. A marked-content number before the Span (as in list
    bodies of a PowerPoint export) must not make the tool pick the Span before it, which was already fine."""
    pdf = build(("Document", [("P", [1, ("Span", "First point", (72, 700)), ("Span", "Second point", (72, 660))])]))
    pdf.Root["/Lang"] = String("en")
    first, second = [o for o in pdf.objects if isinstance(o, pikepdf.Dictionary) and o.get("/S") == Name.Span]
    first["/Lang"], second["/Lang"] = String("en"), String("")
    pdf.save(tmp_path / "list.pdf")

    found = [v for v in run_verapdf(str(tmp_path / "list.pdf")) if v.rule_id == "7.2-29"]
    assert len(found) == 1 and "/K[1](" in found[0].context                # the second structure element
    with pikepdf.open(tmp_path / "list.pdf") as pdf:
        element = detect_affected_element(found[0], pdf)
        assert element.get("/S") == Name.Span and str(element.get("/Lang")) == "" and list(element.K) == [2]
