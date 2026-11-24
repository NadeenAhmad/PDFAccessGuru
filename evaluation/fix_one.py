"""
Runs the frozen PDFAccessGuru version (1.1.0) on ONE file and writes result.json next to the fixed PDF.
Started by run.py with the frozen Python (evaluation/work/venv), one process per file.

    python fix_one.py INPUT.pdf OUTPUT_FOLDER SETTING      (SETTING: rules | local | luna)

The AI requests are the tool's own; this script only notes the request ids of paid requests
(so their exact price can be looked up) and never sees or stores the key.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

SETTINGS = {
    "rules": {"PDFACCESSGURU_AI": "none", "PDFACCESSGURU_PRIVACY": "local"},
    "local": {"PDFACCESSGURU_AI": "ollama", "PDFACCESSGURU_PRIVACY": "local"},
    "luna": {"PDFACCESSGURU_AI": "openrouter"},           # the default online model for an OpenRouter key: GPT-6 Luna
    # Gemma 4 through OpenRouter instead of on this computer (2026-11-11: the local runs made the laptop too hot
    # and slow). OpenRouter has no E4B, so this is the larger Gemma 4 26B of the same family.
    "gemma": {"PDFACCESSGURU_AI": "openrouter", "PDFACCESSGURU_TEXT_MODEL": "google/gemma-4-26b-a4b-it",
              "PDFACCESSGURU_VISION_MODEL": "google/gemma-4-26b-a4b-it"},
}


def main(source: Path, folder: Path, setting: str) -> int:
    os.environ.update(SETTINGS[setting])
    os.environ["PDFACCESSGURU_NO_UPDATE_CHECK"] = "1"
    folder.mkdir(parents=True, exist_ok=True)

    import requests

    from pdfaccessguru import __version__
    from pdfaccessguru.LLM import client
    from pdfaccessguru.pipeline.pipeline import run_pipeline
    from pdfaccessguru.reporting import build_report_metrics

    paid: list[dict] = []
    original_post = requests.post

    def noting_post(url, *args, **kwargs):
        response = original_post(url, *args, **kwargs)
        if "openrouter.ai" in str(url) or "api.openai.com" in str(url):
            try:
                request_id = response.json().get("id", "")
            except ValueError:
                request_id = ""
            entry = {"id": request_id, "model": (kwargs.get("json") or {}).get("model", ""), "status": response.status_code}
            paid.append(entry)
            with (folder / "paid.jsonl").open("a", encoding="utf-8") as handle:   # kept even if the run is stopped
                handle.write(json.dumps(entry) + "\n")
        return response

    client.requests.post = noting_post
    settings = client.settings(refresh=True)
    result = {"version": __version__, "setting": setting, "source": source.name, "ai": settings.describe(),
              "ok": False, "error": "", "seconds": None}
    started = time.perf_counter()
    try:
        report = run_pipeline(str(source), str(folder / "fixed.pdf"))
        result["seconds"] = round(time.perf_counter() - started, 1)
        (folder / "report.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        metrics = build_report_metrics(report)
        phases = {phase["name"]: phase.get("summary") for phase in report.get("phases", []) if phase.get("summary")}
        document = report.get("document_metrics", {})
        result.update(
            ok=True,
            passes=metrics.passes_verapdf,
            problems_before=metrics.detected_count,
            problems_after=metrics.remaining_count,
            problems_fixed=metrics.corrected_count,
            rules_before=phases.get("detection", {}).get("total_distinct_violations"),
            rules_after=phases.get("verification", {}).get("total_distinct_violations"),
            review_items=len(metrics.review_items),
            tagged_share_before=document.get("text_tagging_input", {}).get("tagged_share"),
            tagged_share_after=document.get("text_tagging_output", {}).get("tagged_share"),
            contrast_low=document.get("contrast", {}).get("low_count"),
            ai_requests=dict(client.usage),
        )
    except Exception as error:
        result["seconds"] = round(time.perf_counter() - started, 1)
        result["error"] = f"{type(error).__name__}: {error}"[:500]
        (folder / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
    result["paid_requests"] = paid
    (folder / "result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3]))
