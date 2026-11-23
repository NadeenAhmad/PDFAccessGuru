"""
Makes the examples the guided tour shows (1.1.3): one example chart, and what PDFAccessGuru really writes for it
with each choice. Run from code/PDFAccessGuru with the package importable (needs Ollama with gemma4:e4b and an
OpenRouter key for the two AI examples):

    PYTHONPATH=src python scripts/make_tour_examples.py

Writes src/pdfaccessguru/webapp/static/tour-chart.png and src/pdfaccessguru/webapp/static/tour-examples.json.
The texts are copied from the files the tool makes; nothing is written by hand.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pikepdf
import pymupdf as fitz
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src" / "pdfaccessguru" / "webapp" / "static"
DATA = [("2023", 8, 10), ("2024", 12, 19), ("2025", 15, 31), ("2026", 20, 44)]   # year, staff, students


def font(size: int, bold: bool = False):
    for name in (("Arial Bold.ttf", "Arial.ttf")[not bold], "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"):
        for folder in ("/System/Library/Fonts/Supplemental", "/Library/Fonts", "/usr/share/fonts/truetype/dejavu"):
            if (Path(folder) / name).exists():
                return ImageFont.truetype(str(Path(folder) / name), size)
    return ImageFont.load_default()


def chart() -> Image.Image:
    """Grouped bars (staff, students) with a legend: enough content for the three detail levels to differ."""
    w, h = 1200, 640
    image = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(image)
    draw.text((60, 24), "Participants per year", fill="black", font=font(40, True))
    colours = {"Staff": (31, 92, 153), "Students": (230, 145, 40)}
    for number, (name, colour) in enumerate(colours.items()):
        x = 760 + number * 200
        draw.rectangle((x, 36, x + 28, 64), fill=colour)
        draw.text((x + 38, 32), name, fill="black", font=font(28))
    left, bottom, top = 140, h - 90, 130
    draw.line((left, top, left, bottom), fill="black", width=3)
    draw.line((left, bottom, w - 60, bottom), fill="black", width=3)
    for tick in range(0, 51, 10):
        y = bottom - (bottom - top) * tick / 50
        draw.line((left - 10, y, left, y), fill="black", width=2)
        draw.text((left - 70, y - 16), str(tick), fill="black", font=font(28))
    step = (w - 60 - left) / len(DATA)
    for i, (year, *values) in enumerate(DATA):
        for j, (value, colour) in enumerate(zip(values, colours.values())):
            x0 = left + i * step + step * (0.12 + 0.38 * j)
            y = bottom - (bottom - top) * value / 50
            draw.rectangle((x0, y, x0 + step * 0.34, bottom), fill=colour)
            draw.text((x0 + step * 0.08, y - 40), str(value), fill="black", font=font(28, True))
        draw.text((left + i * step + step * 0.36, bottom + 16), year, fill="black", font=font(30))
    return image


def example_pdf(path: Path, picture: bytes) -> None:
    """One page as an office export would leave it: no tags, a heading, a sentence and the chart."""
    archive = fitz.Archive()
    archive.add(picture, "chart.png")
    story = fitz.Story(html='<h1>Interest in the workshop</h1><p>The workshop has grown every year since it started '
                            'in 2023, among staff and students.</p><img src="chart.png" width="400"/>',
                       user_css="body { font-family: sans-serif; font-size: 11pt; }", archive=archive)
    writer = fitz.DocumentWriter(str(path))
    device = writer.begin_page(fitz.paper_rect("a4"))
    story.place(fitz.paper_rect("a4") + (56, 56, -56, -56))
    story.draw(device)
    writer.end_page()
    writer.close()


def run(source: Path, folder: Path, *options: str, environment: dict | None = None) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / "example_accessible.pdf"
    env = {**os.environ, "PDFACCESSGURU_NO_UPDATE_CHECK": "1", **(environment or {})}
    subprocess.run([sys.executable, "-c", "from pdfaccessguru.cli import main; main()", "fix", str(source), "-o", str(out),
                    "--overwrite", *options], check=True, env=env, stdout=subprocess.DEVNULL)
    return out


def figure_text(pdf: Path) -> str:
    with pikepdf.open(pdf) as document:
        texts = [str(element.get("/Alt", "")) for element in _elements(document.Root.StructTreeRoot)
                 if element.get("/S") == "/Figure"]
    if len(texts) != 1 or not texts[0]:
        raise SystemExit(f"expected one figure with a description in {pdf}, found {texts}")
    return texts[0]


def _elements(node):
    kids = node.get("/K")
    for kid in (kids if isinstance(kids, pikepdf.Array) else [kids] if kids is not None else []):
        if isinstance(kid, pikepdf.Dictionary) and kid.get("/S") is not None:
            yield kid
            yield from _elements(kid)


def report_lines(path: Path) -> dict:
    """Three summary lines of the real report, and the first picture item of its review list."""
    lines = path.read_text(encoding="utf-8").splitlines()
    wanted = ("Passes the automatic check", "Problems fixed", "Texts the tool wrote for you to review")
    summary = [line[2:].split(" (")[0] for line in lines if line.startswith("- ") and line[2:].startswith(wanted)]
    heading = next(line[4:] for line in lines if line.startswith("### Descriptions of pictures"))
    start = lines.index("### " + heading)
    item = next(line[2:] for line in lines[start:] if line.startswith("- ") and "The tool wrote" in line)
    return {"summary": summary, "review_heading": heading, "review_item": item}


COLOURS = {"grey": (170, 170, 170), "orange": (245, 166, 35), "blue": (110, 170, 230)}   # common pale text colours


def contrast_examples() -> list[dict]:
    """What the contrast fix really does to pale text on white (the same function the tool uses)."""
    from pdfaccessguru.pipeline.contrast import better_color, contrast_ratio

    white, rows = (255, 255, 255), []
    for name, before in COLOURS.items():
        after = better_color(before, white, 4.5)
        rows.append({"name": name, "before": "#%02x%02x%02x" % before, "after": "#%02x%02x%02x" % after,
                     "ratio_before": round(contrast_ratio(before, white), 1),
                     "ratio_after": round(contrast_ratio(after, white), 1)})
    return rows


def main() -> None:
    if "--contrast-only" in sys.argv:                 # keep the AI texts, recompute only the colour examples
        path = STATIC / "tour-examples.json"
        examples = json.loads(path.read_text(encoding="utf-8"))
        examples["contrast"] = contrast_examples()
        path.write_text(json.dumps(examples, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(examples["contrast"], indent=1))
        return

    image = chart()
    small = image.resize((600, 320), Image.LANCZOS)
    buffer = io.BytesIO()
    small.convert("P", palette=Image.ADAPTIVE, colors=32).save(buffer, format="PNG", optimize=True)
    (STATIC / "tour-chart.png").write_bytes(buffer.getvalue())
    big = io.BytesIO()
    image.save(big, format="PNG")
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        source = work / "example.pdf"
        example_pdf(source, big.getvalue())
        local = {"PDFACCESSGURU_VISION_MODEL": "gemma4:e4b", "PDFACCESSGURU_TEXT_MODEL": "gemma4:e4b"}
        texts = {
            "rules": figure_text(run(source, work / "rules", "--ai", "none")),
            "local": {level: figure_text(run(source, work / f"local-{level}", "--ai", "ollama", "--descriptions", level,
                                             "--review-list", environment=local))
                      for level in ("brief", "standard", "detailed")},
            "online": {level: figure_text(run(source, work / f"online-{level}", "--ai", "openrouter", "--descriptions",
                                              level)) for level in ("brief", "standard", "detailed")},
        }
        report = report_lines(work / "local-standard" / "example_accessible_report.md")
    examples = {
        "texts": texts,
        "local_model": "gemma4:e4b",
        "online_model": "openai/gpt-6-luna",
        "report": report,
        "contrast": contrast_examples(),
    }
    (STATIC / "tour-examples.json").write_text(json.dumps(examples, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(examples, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
