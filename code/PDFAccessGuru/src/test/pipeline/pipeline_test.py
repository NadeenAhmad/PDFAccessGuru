"""
End-to-end tests of the staged pipeline with real veraPDF runs: kept fixes, undone fixes, and
the guarantee that the original file is never changed.
"""

import shutil
from collections import Counter
from pathlib import Path

import pikepdf
import pytest

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors import corrector as corrector_registry
from pdfaccessguru.pipeline.pipeline import run_pipeline
from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf

CORPUS = Path(__file__).resolve().parents[1] / "resources" / "veraPDF_corpus"


def _copy(name: str, tmp_path: Path) -> Path:
    target = tmp_path / name
    shutil.copy(CORPUS / name, target)
    return target


def _lines(report: dict, level: str) -> list[str]:
    return [line["message"] for phase in report["phases"] for line in phase["lines"] if line["level"] == level]


def test_a_good_fix_is_kept_and_the_original_is_untouched(tmp_path):
    source = _copy("7.5-t01-fail-a.pdf", tmp_path)
    original = source.read_bytes()
    output = tmp_path / "out.pdf"
    steps = []

    report = run_pipeline(str(source), str(output), progress_callback=lambda text, fraction: steps.append((text, fraction)))

    assert source.read_bytes() == original
    assert run_verapdf(str(output)) == []
    assert any("7.5-1: 1 problem(s) disappeared" in m for m in _lines(report, "info"))
    assert steps[0][0] == "Checking the file" and steps[-1] == ("Done", 1.0)
    stages = [p.get("stage") for p in report["phases"] if p["name"] == "correction"]
    assert stages == ["table_headers"]


def test_a_fix_that_breaks_an_earlier_stage_is_undone(tmp_path, monkeypatch):
    source = _copy("7.5-t01-fail-a.pdf", tmp_path)
    output = tmp_path / "out.pdf"

    def harmful(detected_violation, pdf):
        del pdf.Root["/MarkInfo"]          # breaks rule 6.2-1 (structure stage, earlier)

    monkeypatch.setitem(corrector_registry.CORRECTOR_FUNCTIONS, "td-headers-missing", harmful)
    report = run_pipeline(str(source), str(output))

    warnings = _lines(report, "warn")
    assert any("7.5-1 were undone" in m and "fixed nothing" in m for m in warnings)
    remaining = Counter(v.rule_id for v in run_verapdf(str(output)))
    assert remaining["6.2-1"] == 0                      # the harmful fix is gone: the tagged mark is back
    with pikepdf.open(output) as corrected:
        assert corrected.Root.MarkInfo.Marked
    assert remaining["7.5-1"] <= 1                      # (the table header itself is fixed in Phase 10's meaning step)


def test_a_fix_that_changes_how_a_page_looks_is_undone(tmp_path, monkeypatch):
    source = _copy("7.1-t03-fail-a.pdf", tmp_path)
    output = tmp_path / "out.pdf"
    before = Counter(v.rule_id for v in run_verapdf(str(source)))
    assert before["7.1-3"] > 0

    def deletes_text(detected_violation, pdf):
        for page in pdf.pages:
            kept = [(ops, op) for ops, op in pikepdf.parse_content_stream(page) if str(op) not in ("Tj", "TJ")]
            page.obj["/Contents"] = pdf.make_stream(pikepdf.unparse_content_stream(kept))

    monkeypatch.setitem(corrector_registry.CORRECTOR_FUNCTIONS, "content-neither-artifact-nor-tagged-content", deletes_text)
    report = run_pipeline(str(source), str(output))

    # 7.1-3 is checked by character positions (it may tag a file anew), so the reason names the characters
    assert any("7.1-3 were undone" in m and ("look different" in m or "disappear" in m) for m in _lines(report, "warn"))
    with pikepdf.open(source) as original, pikepdf.open(output) as corrected:
        def text_ops(pdf):
            return sum(str(op) in ("Tj", "TJ") for page in pdf.pages for _, op in pikepdf.parse_content_stream(page))
        assert text_ops(corrected) == text_ops(original)


def test_output_must_not_replace_the_input(tmp_path):
    source = _copy("7.5-t01-fail-a.pdf", tmp_path)
    with pytest.raises(ValueError):
        run_pipeline(str(source), str(source))
