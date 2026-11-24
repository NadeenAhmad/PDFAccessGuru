"""
Picture descriptions by PDFAccessGuru 1.1 (its prompt for the chosen level of detail, the abbreviations the whole
document defines, its checks and length safeguard) for captured pictures, with Gemma 4 26B through OpenRouter.
Run with the Python of evaluation/work/venv (PDFAccessGuru as installed from PyPI).

    python describe_pictures.py PICTURES.json OUTPUT.json [brief|standard|detailed]

PICTURES.json: selection.json (items with "id", "folder", "picture") or a preview/pilot file (items with "file",
"picture"). Paid request ids go to OUTPUT.json.paid.jsonl; log their prices with budget.record afterwards.
If the tool's checks reject an answer, the tool would use its simple rules: that is recorded, not hidden.
"""

from __future__ import annotations

import csv
import importlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

from paths import KUMAR, WORK
SETS = Path(__file__).resolve().parent / "results" / "sets"
FIGURE_FIX = ("pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle."
              "7_3_t01_figure_structure_alternate_description_missing")
MODEL = "google/gemma-4-26b-a4b-it"


def main(pictures_file: Path, output_file: Path, level: str = "standard") -> int:
    os.environ.update({"PDFACCESSGURU_NO_UPDATE_CHECK": "1", "PDFACCESSGURU_AI": "openrouter",
                       "PDFACCESSGURU_VISION_MODEL": MODEL, "PDFACCESSGURU_TEXT_MODEL": MODEL,
                       "PDFACCESSGURU_DESCRIPTIONS": level})
    os.environ.pop("PDFACCESSGURU_PRIVACY", None)
    import pymupdf
    import requests

    from pdfaccessguru import __file__ as package_file
    from pdfaccessguru.LLM import client
    from pdfaccessguru.LLM.descriptions import abbreviation_definitions

    print("PDFAccessGuru code from", Path(package_file).parent, flush=True)
    figure_fix = importlib.import_module(FIGURE_FIX)
    kumar_files = {row["run_id"]: row["file"] for row in csv.DictReader(open(SETS / "kumar.csv", encoding="utf-8"))}
    items = json.loads(pictures_file.read_text(encoding="utf-8"))
    results = json.loads(output_file.read_text(encoding="utf-8")) if output_file.exists() else {}
    paid_log = Path(str(output_file) + ".paid.jsonl")
    original_post = requests.post

    def noting_post(url, *args, **kwargs):
        response = original_post(url, *args, **kwargs)
        if "openrouter.ai" in str(url):
            try:
                request_id = response.json().get("id", "")
            except ValueError:
                request_id = ""
            with paid_log.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"id": request_id, "model": (kwargs.get("json") or {}).get("model", "")}) + "\n")
        return response

    client.requests.post = noting_post
    client.settings(refresh=True)
    abbreviations_of: dict[str, list[str]] = {}
    for number, item in enumerate(items, start=1):
        folder = Path(item["folder"]) if "folder" in item else WORK / "pictures" / item["file"]
        key = item.get("id") or f"p{number:02d}"
        if key in results:
            continue
        run_id = folder.name
        if run_id not in abbreviations_of:
            with pymupdf.open(KUMAR / kumar_files[run_id]) as document:
                text = " ".join(page.get_text() for page in document)
            abbreviations_of[run_id] = abbreviation_definitions(" ".join(text.split()))
        picture = next(p for p in json.loads((folder / "pictures.json").read_text(encoding="utf-8"))
                       if p["picture"] == item["picture"])
        png = (folder / f"{item['picture']}.png").read_bytes()
        try:
            answer = figure_fix.generate_figure_alt_text(picture["context_json"], SimpleNamespace(image_data=png),
                                                         abbreviations_of[run_id])
            text = figure_fix._validate_alt_text(answer, SimpleNamespace(violation=SimpleNamespace(name="figure-alt-text")))
            how = "ai"
        except Exception as error:                       # the tool would use its simple rules here
            text, how = picture.get("rules", ""), f"rules fallback ({type(error).__name__}: {str(error)[:120]})"
        results[key] = {"file": run_id, "picture": item["picture"], "level": level, "text": text, "how": how,
                        "abbreviations": abbreviations_of[run_id], "rules": picture.get("rules", "")}
        output_file.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{key}: {how[:40]} ({len(text)} characters)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3] if len(sys.argv) > 3 else "standard"))
