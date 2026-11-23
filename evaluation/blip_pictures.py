"""
Non-LLM baseline for picture descriptions: BLIP image captioning (Li et al., ICML 2022; Salesforce
blip-image-captioning-large), a computer-vision captioning model without a language-model prompt. It sees only
the picture (no caption, no nearby text), like captioning tools that are used for alt text. Runs on this
computer, on at most 2 processor cores; no cost. Decoding: beam search (3 beams, up to 40 tokens) with the usual
guards against repeating words (no repeated 3-word sequence, repetition penalty 1.2); without them BLIP repeats
itself on charts ("a blue line and a red line and a blue line ..."), which would make the baseline look worse
than it is.

    venv-blip/bin/python blip_pictures.py PICTURES.json OUTPUT.json

PICTURES.json: selection.json (items with "id", "folder", "picture") or a preview file (items with "file",
"picture"). Setup: Python 3.11, torch 2.2.2 (the last version for Intel Macs), transformers 4.44.2.
"""

from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

from paths import WORK
MODEL = "Salesforce/blip-image-captioning-large"


def main(pictures_file: Path, output_file: Path) -> int:
    import torch
    from PIL import Image
    from transformers import BlipForConditionalGeneration, BlipProcessor

    torch.set_num_threads(2)
    processor = BlipProcessor.from_pretrained(MODEL)
    model = BlipForConditionalGeneration.from_pretrained(MODEL).eval()
    items = json.loads(pictures_file.read_text(encoding="utf-8"))
    results = json.loads(output_file.read_text(encoding="utf-8")) if output_file.exists() else {}
    for number, item in enumerate(items, start=1):
        key = item.get("id") or f"p{number:02d}"
        if key in results:
            continue
        folder = Path(item["folder"]) if "folder" in item else WORK / "pictures" / item["file"]
        image = Image.open(io.BytesIO((folder / f"{item['picture']}.png").read_bytes())).convert("RGB")
        started = time.perf_counter()
        with torch.no_grad():
            output = model.generate(**processor(images=image, return_tensors="pt"), max_new_tokens=40, num_beams=3,
                                    no_repeat_ngram_size=3, repetition_penalty=1.2)
        text = processor.decode(output[0], skip_special_tokens=True).strip()
        text = text[:1].upper() + text[1:] + ("" if text.endswith(".") else ".")
        results[key] = {"file": folder.name, "picture": item["picture"], "text": text, "model": MODEL,
                        "seconds": round(time.perf_counter() - started, 1)}
        output_file.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{key}: {text}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()))
