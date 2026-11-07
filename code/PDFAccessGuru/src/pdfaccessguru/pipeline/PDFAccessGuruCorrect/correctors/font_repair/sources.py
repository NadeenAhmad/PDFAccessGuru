"""
Where to get a font program for a font that a PDF uses but does not contain.

1. The same font installed on this computer (matched by its name, e.g. "Arial,Bold" and
   "Arial-BoldMT"), if its licence allows embedding.
2. Otherwise, for the standard office fonts, a free font with exactly the same character
   widths: Liberation Sans (Arial, Helvetica), Liberation Serif (Times New Roman, Times) and
   Liberation Mono (Courier New, Courier). Viewers already show such a look-alike today,
   because the font is missing from the file.
"""

from __future__ import annotations

import json
import os
import platform
import re
from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTCollection, TTFont
from platformdirs import user_cache_dir

from pdfaccessguru.external_tools import find_fallback_fonts

_RESTRICTED = 0x0002          # OS/2 fsType: the font's licence forbids embedding
_BITMAP_ONLY = 0x0200

_TWINS = {
    "arial": "LiberationSans", "helvetica": "LiberationSans",
    "timesnewroman": "LiberationSerif", "times": "LiberationSerif",
    "couriernew": "LiberationMono", "courier": "LiberationMono",
}
_STYLE_FILE = {"": "Regular", "bold": "Bold", "italic": "Italic", "bolditalic": "BoldItalic"}


@dataclass(frozen=True)
class FontSource:
    path: str
    index: int              # font number inside a .ttc collection
    postscript_name: str
    exact: bool             # the same font as the PDF names (not a look-alike)

    def load(self) -> TTFont:
        return TTFont(self.path, fontNumber=self.index) if self.path.lower().endswith(".ttc") else TTFont(self.path)


def normalize(name: str) -> str:
    """'TimesNewRomanPS-BoldItalicMT', 'Times New Roman,BoldItalic' -> 'timesnewromanbolditalic'."""
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    key = re.sub(r"mt$", "", key)
    key = re.sub(r"ps(?=(bold|italic|oblique)*$)", "", key)
    key = re.sub(r"regular$", "", key)
    return key.replace("oblique", "italic")


def split_style(name: str, font_flags: int = 0, weight: float = 0, italic_angle: float = 0) -> tuple[str, str]:
    """(family key, style) of a font name: 'Arial,BoldItalic' -> ('arial', 'bolditalic')."""
    key = normalize(name)
    bold = italic = False
    while True:
        if key.endswith("italic"):
            key, italic = key[:-6], True
        elif key.endswith("bold"):
            key, bold = key[:-4], True
        else:
            break
    if key == "timesroman":
        key = "times"
    bold = bold or bool(font_flags & (1 << 18)) or weight >= 700
    italic = italic or bool(font_flags & 64) or italic_angle != 0
    return key, ("bold" if bold else "") + ("italic" if italic else "")


def _font_dirs() -> list[Path]:
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        return [Path("/System/Library/Fonts"), Path("/Library/Fonts"), home / "Library/Fonts"]
    if system == "Windows":
        windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
        local = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local"))
        return [windows / "Fonts", local / "Microsoft/Windows/Fonts"]
    return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), home / ".fonts", home / ".local/share/fonts"]


def _describe(font: TTFont, path: Path, index: int) -> dict | None:
    if "glyf" not in font or "OS/2" not in font:
        return None                                     # only TrueType outlines can be embedded here
    names = font["name"]
    postscript = names.getDebugName(6) or ""
    full = names.getDebugName(4) or ""
    return {"path": str(path), "index": index, "ps": postscript, "full": full, "fsType": int(font["OS/2"].fsType)}


class _SystemFonts:
    """Index of installed TrueType fonts by name, cached on disk (rebuilt when fonts change)."""

    _entries: list[dict] | None = None

    @classmethod
    def entries(cls) -> list[dict]:
        if cls._entries is not None:
            return cls._entries
        cache_file = Path(user_cache_dir("pdfaccessguru")) / "font-index.json"
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            cache = {}
        entries, fresh = [], {}
        for folder in _font_dirs():
            if not folder.is_dir():
                continue
            for path in folder.rglob("*"):
                if path.suffix.lower() not in (".ttf", ".ttc"):
                    continue
                try:
                    stamp = f"{path.stat().st_mtime_ns}:{path.stat().st_size}"
                except OSError:
                    continue
                cached = cache.get(str(path))
                if cached is not None and cached["stamp"] == stamp:
                    described = cached["fonts"]
                else:
                    described = []
                    try:
                        fonts = TTCollection(str(path), lazy=True).fonts if path.suffix.lower() == ".ttc" \
                            else [TTFont(str(path), lazy=True)]
                        for index, font in enumerate(fonts):
                            info = _describe(font, path, index)
                            if info is not None:
                                described.append(info)
                    except Exception:
                        described = []
                fresh[str(path)] = {"stamp": stamp, "fonts": described}
                entries.extend(described)
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(fresh), encoding="utf-8")
        except OSError:
            pass
        cls._entries = entries
        return entries


def find_source(name: str, font_flags: int = 0, weight: float = 0, italic_angle: float = 0,
                use_system_fonts: bool = True) -> FontSource | None:
    """The best available font program for a font that is not embedded, or None."""
    family, style = split_style(name, font_flags, weight, italic_angle)
    if use_system_fonts:
        for entry in _SystemFonts.entries():
            if entry["fsType"] & (_RESTRICTED | _BITMAP_ONLY):
                continue
            if family + style in (normalize(entry["ps"]), normalize(entry["full"])) or \
                    split_style(entry["ps"]) == (family, style):
                return FontSource(entry["path"], entry["index"], entry["ps"], exact=True)
    twin = _TWINS.get(family)
    folder = find_fallback_fonts()
    if twin is None or folder is None:
        return None
    path = folder / f"{twin}-{_STYLE_FILE[style]}.ttf"
    return FontSource(str(path), 0, f"{twin}-{_STYLE_FILE[style]}", exact=False) if path.is_file() else None
