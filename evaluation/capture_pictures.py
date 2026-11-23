"""
Captures, for every picture PDFAccessGuru 1.0.3 describes in a file, exactly what an AI model gets for it
(the rendered picture and its context) and what the simple rules write instead. Runs the frozen tool with
no AI, so it costs nothing. Used to give all models in the picture comparison identical input.

    python capture_pictures.py INPUT.pdf OUTPUT_FOLDER          (frozen Python)

Writes OUTPUT_FOLDER/pictures.json and one PNG per picture.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
from pathlib import Path

FIGURE_FIX = ("pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_5_brian_karle."
              "7_3_t01_figure_structure_alternate_description_missing")
PICTURE_RULES = "pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.pictures"


def main(source: Path, folder: Path) -> int:
    os.environ.update({"PDFACCESSGURU_AI": "none", "PDFACCESSGURU_PRIVACY": "local", "PDFACCESSGURU_NO_UPDATE_CHECK": "1"})
    folder.mkdir(parents=True, exist_ok=True)
    from pdfaccessguru.pipeline.pipeline import run_pipeline

    figure_fix = importlib.import_module(FIGURE_FIX)
    picture_rules = importlib.import_module(PICTURE_RULES)
    captured: list[dict] = []

    original_ai = figure_fix._alt_text_from_ai

    def capture_ai(context_json, rendered_figure, detected_violation):
        png = rendered_figure.image.image_data
        key = hashlib.sha1(png + context_json.encode("utf-8")).hexdigest()[:12]
        (folder / f"{key}.png").write_bytes(png)
        captured.append({"picture": key, "page": rendered_figure.page_index + 1, "context_json": context_json})
        return original_ai(context_json, rendered_figure, detected_violation)   # no AI set up: None, so the rules write

    original_rules = picture_rules.describe_picture

    def capture_rules(*args, **kwargs):
        text, how = original_rules(*args, **kwargs)
        if captured and "rules" not in captured[-1]:
            captured[-1].update(rules=text, rules_source=how)
        return text, how

    figure_fix._alt_text_from_ai = capture_ai
    picture_rules.describe_picture = capture_rules
    run_pipeline(str(source), str(folder / "fixed-rules.pdf"))
    (folder / "pictures.json").write_text(json.dumps(captured, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{source.name}: {len(captured)} pictures")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()))
