"""
Repairs inside embedded font programs. None of them changes which glyph a character shows or
where it is placed: each first works out the glyph a viewer uses today (ISO 32000-1, 9.6.6.4)
and then records that same choice in the form PDF/UA requires.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from pikepdf import Array, Dictionary, Name, Pdf, Stream

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.fonts import (
    FLAG_NONSYMBOLIC, FLAG_SYMBOLIC, all_fonts, base_name, flags, font_program, glyph_names, is_embedded,
    store_program, unicode_of, used_codes,
)


@dataclass
class ProgramResult:
    fixed: list[str] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)


def _is_symbolic(font: Dictionary) -> bool:
    value = flags(font)
    return bool(value & FLAG_SYMBOLIC) and not value & FLAG_NONSYMBOLIC


def _subtable(program: TTFont, platform: int, encoding: int):
    if "cmap" not in program:
        return None
    return next((t for t in program["cmap"].tables if (t.platformID, t.platEncID) == (platform, encoding)), None)


def glyph_for_code(program: TTFont, font: Dictionary, code: int, names: dict[int, str] | None) -> str | None:
    """The glyph a viewer shows for a character code of a simple TrueType font (9.6.6.4)."""
    microsoft_unicode = _subtable(program, 3, 1)
    microsoft_symbol = _subtable(program, 3, 0)
    mac_roman = _subtable(program, 1, 0)
    if not _is_symbolic(font) and names is not None:
        name = names.get(code)
        text = unicode_of(name) if name else ""
        if microsoft_unicode is not None and len(text) == 1 and ord(text) in microsoft_unicode.cmap:
            return microsoft_unicode.cmap[ord(text)]
        if mac_roman is not None and code in mac_roman.cmap:
            return mac_roman.cmap[code]
    if microsoft_symbol is not None:
        for key in (code, 0xF000 + code, 0xF100 + code, 0xF200 + code):
            if key in microsoft_symbol.cmap:
                return microsoft_symbol.cmap[key]
    if mac_roman is not None and code in mac_roman.cmap:
        return mac_roman.cmap[code]
    if "post" in program and names is not None and names.get(code) in program.getGlyphOrder():
        return names[code]
    return None


def _simple_truetype_fonts(pdf: Pdf):
    for font in all_fonts(pdf):
        if font.get("/Subtype") != Name.TrueType:
            continue
        loaded = font_program(font)
        if loaded is not None:
            yield font, loaded[0], loaded[1]


def match_widths(pdf: Pdf) -> ProgramResult:
    """
    Rule 7.21.5-1: make the embedded program's glyph widths equal to the widths written in the
    PDF. The PDF widths decide where text is placed, so the page does not change. (The first
    version changed the PDF widths instead, which moves text.)
    """
    result = ProgramResult()
    usage = used_codes(pdf)
    for font in all_fonts(pdf):
        subtype = font.get("/Subtype")
        used = usage.get(font.objgen) if font.is_indirect else None
        if not used:
            continue                    # only characters shown on the pages are checked
        if subtype == Name.TrueType:
            outcome = _match_simple_widths(pdf, font, used)
        elif subtype == Name.Type0:
            outcome = _match_cid_widths(pdf, font, used)
        else:
            continue
        if outcome is True:
            result.fixed.append(base_name(font))
        elif isinstance(outcome, str):
            result.skipped.append((base_name(font), outcome))
    return result


def _set_advance(program: TTFont, glyph: str, pdf_width: float, decided: dict[str, float]) -> bool | str:
    hmtx = program["hmtx"]
    units = program["head"].unitsPerEm
    current = hmtx[glyph][0] * 1000 / units
    if abs(current - pdf_width) <= 1:
        return False
    if glyph in decided:
        return False                  # one glyph shown with two widths: only one can match
    decided[glyph] = pdf_width
    hmtx[glyph] = (round(pdf_width * units / 1000), hmtx[glyph][1])
    return True


def _match_simple_widths(pdf: Pdf, font: Dictionary, used: set[int]):
    loaded = font_program(font)
    widths, first = font.get("/Widths"), font.get("/FirstChar")
    if loaded is None or not isinstance(widths, Array) or first is None or "hmtx" not in loaded[0]:
        return None
    program, key = loaded
    names = glyph_names(font)
    decided: dict[str, float] = {}
    changed = False
    for index, width in enumerate(widths):
        code = int(first) + index
        if code not in used:
            continue
        glyph = glyph_for_code(program, font, code, names)
        if glyph is None or glyph == ".notdef":
            continue
        outcome = _set_advance(program, glyph, float(width), decided)
        if isinstance(outcome, str):
            return outcome
        changed = changed or outcome
    if changed:
        store_program(pdf, font, program, key)
    return changed


def _cid_widths(cid_font: Dictionary) -> dict[int, float]:
    widths: dict[int, float] = {}
    entries = cid_font.get("/W")
    if not isinstance(entries, Array):
        return widths
    items = list(entries)
    index = 0
    while index < len(items):
        start = int(items[index])
        following = items[index + 1] if index + 1 < len(items) else None
        if isinstance(following, Array):
            for offset, width in enumerate(following):
                widths[start + offset] = float(width)
            index += 2
        elif index + 2 < len(items):
            for cid in range(start, int(following) + 1):
                widths[cid] = float(items[index + 2])
            index += 3
        else:
            break
    return widths


def _match_cid_widths(pdf: Pdf, font: Dictionary, used: set[int]):
    descendants = font.get("/DescendantFonts")
    cid_font = descendants[0] if isinstance(descendants, Array) and len(descendants) else None
    if not isinstance(cid_font, Dictionary) or cid_font.get("/Subtype") != Name.CIDFontType2:
        return None
    loaded = font_program(font)
    if loaded is None or "hmtx" not in loaded[0]:
        return None
    program, key = loaded
    mapping = cid_font.get("/CIDToGIDMap", Name.Identity)
    gid_of = None
    if isinstance(mapping, Stream):
        data = mapping.read_bytes()
        gid_of = lambda cid: (data[2 * cid] << 8 | data[2 * cid + 1]) if 2 * cid + 1 < len(data) else None
    elif mapping == Name.Identity:
        gid_of = lambda cid: cid
    else:
        return "the glyph map of the font is invalid"
    order = program.getGlyphOrder()
    decided: dict[str, float] = {}
    changed = False
    for cid, width in _cid_widths(cid_font).items():
        if cid not in used:
            continue
        gid = gid_of(cid)
        if gid is None or gid <= 0 or gid >= len(order):
            continue
        outcome = _set_advance(program, order[gid], width, decided)
        if isinstance(outcome, str):
            return outcome
        changed = changed or outcome
    if changed:
        store_program(pdf, font, program, key)
    return changed


def add_unicode_cmap(pdf: Pdf) -> ProgramResult:
    """
    Rule 7.21.6-1: a non-symbolic TrueType font needs a Unicode (3,1) or Mac (1,0) character
    table. A (3,1) table is added that maps each character to the glyph viewers use today.
    """
    result = ProgramResult()
    for font, program, key in _simple_truetype_fonts(pdf):
        if _is_symbolic(font) or "cmap" not in program:
            continue
        if _subtable(program, 3, 1) is not None or _subtable(program, 1, 0) is not None:
            continue
        names = glyph_names(font)
        if names is None:
            result.skipped.append((base_name(font), "the font's encoding cannot be read"))
            continue
        mapping = {}
        for code, name in names.items():
            text = unicode_of(name)
            glyph = glyph_for_code(program, font, code, names)
            if len(text) == 1 and glyph and glyph != ".notdef":
                mapping.setdefault(ord(text), glyph)
        if not mapping:
            result.skipped.append((base_name(font), "no character could be matched to a glyph"))
            continue
        table = CmapSubtable.newSubtable(4)
        table.platformID, table.platEncID, table.language = 3, 1, 0
        table.cmap = mapping
        program["cmap"].tables.append(table)
        store_program(pdf, font, program, key)
        result.fixed.append(base_name(font))
    return result


def add_symbol_cmap(pdf: Pdf) -> ProgramResult:
    """
    Rule 7.21.6-4: a symbolic TrueType font with several character tables needs the Microsoft
    Symbol (3,0) table. It is added with the glyphs viewers use today; no table is removed
    (the first version removed tables, which can change which glyphs are shown).
    """
    result = ProgramResult()
    for font, program, key in _simple_truetype_fonts(pdf):
        if not _is_symbolic(font) or "cmap" not in program:
            continue
        tables = program["cmap"].tables
        if len(tables) <= 1 or _subtable(program, 3, 0) is not None:
            continue
        first, last = int(font.get("/FirstChar", 0)), int(font.get("/LastChar", 255))
        mapping = {}
        for code in range(first, last + 1):
            glyph = glyph_for_code(program, font, code, None) or next(
                (t.cmap[code] for t in tables if code in t.cmap), None)
            if glyph and glyph != ".notdef":
                mapping[0xF000 + code] = glyph
        if not mapping:
            result.skipped.append((base_name(font), "no character could be matched to a glyph"))
            continue
        table = CmapSubtable.newSubtable(4)
        table.platformID, table.platEncID, table.language = 3, 0, 0
        table.cmap = mapping
        tables.append(table)
        store_program(pdf, font, program, key)
        result.fixed.append(base_name(font))
    return result


def set_identity_cid_to_gid(pdf: Pdf) -> ProgramResult:
    """
    Rule 7.21.3.2-1: an embedded Type 2 CIDFont needs a CIDToGIDMap. When it is missing, viewers
    already use Identity (the default in ISO 32000-1, Table 117), so writing Identity changes
    nothing on the page. An existing map stream is never replaced.
    """
    result = ProgramResult()
    for font in all_fonts(pdf):
        descendants = font.get("/DescendantFonts")
        if font.get("/Subtype") != Name.Type0 or not isinstance(descendants, Array) or not len(descendants):
            continue
        cid_font = descendants[0]
        if not isinstance(cid_font, Dictionary) or cid_font.get("/Subtype") != Name.CIDFontType2 \
                or not is_embedded(font):
            continue
        mapping = cid_font.get("/CIDToGIDMap")
        if isinstance(mapping, Stream) or mapping == Name.Identity:
            continue
        cid_font["/CIDToGIDMap"] = Name.Identity
        result.fixed.append(base_name(font))
    return result
