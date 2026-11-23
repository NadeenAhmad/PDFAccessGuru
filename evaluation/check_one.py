"""
Checks ONE PDF the same way PDFAccessGuru checks its own output (veraPDF, PDF/UA-1) and measures how
much text a screen reader can reach. Used for the other tools' outputs (opendataloader-pdf, Acrobat), so
every tool is measured with the same yardstick. Runs with the frozen Python; changes nothing.

    python check_one.py FILE.pdf RESULT.json
"""

from __future__ import annotations

import collections
import json
import sys
import time
from pathlib import Path


def main(source: Path, target: Path) -> int:
    import pikepdf

    from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
    from pdfaccessguru.pipeline.text_tagging import measure_text_tagging

    result = {"file": source.name, "ok": False, "error": ""}
    started = time.perf_counter()
    try:
        violations = run_verapdf(str(source))
        with pikepdf.open(source) as pdf:
            tagging = measure_text_tagging(pdf)
            pages = len(pdf.pages)
        by_rule = collections.Counter(violation.rule_id for violation in violations)
        result.update(ok=True, passes=not violations, problems=len(violations), rules=len(by_rule),
                      by_rule=dict(by_rule), tagged_share=tagging.get("tagged_share"), pages=pages)
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"[:500]
    result["seconds"] = round(time.perf_counter() - started, 1)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=1), encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()))
