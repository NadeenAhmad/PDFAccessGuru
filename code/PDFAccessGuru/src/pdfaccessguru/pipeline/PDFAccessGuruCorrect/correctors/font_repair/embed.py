"""
Embedding fonts that a PDF uses but does not contain (rule 7.21.4.1-1).

The text keeps its exact position: the character widths written in the PDF are kept, and the
embedded font program is adapted to them. Only simple fonts with a readable encoding are
embedded (in practice: Arial, Helvetica, Times, Courier and other installed text fonts).
Composite fonts (CJK) and symbol fonts need the exact original font file and are left alone.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field

from fontTools.subset import Options, Subsetter
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from pikepdf import Array, Dictionary, Name, Pdf

from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.fonts import (
    FLAG_ITALIC, FLAG_NONSYMBOLIC, FLAG_SYMBOLIC, WIN_ANSI_ENCODING, all_fonts,
    base_name, descriptor, flags, glyph_names, is_embedded, own_descriptor, unicode_of, used_codes,
)
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.sources import FontSource, find_source

_SYMBOL_FONTS = ("symbol", "zapfdingbats", "dingbats", "wingdings", "webdings", "marlett")


@dataclass
class EmbedResult:
    embedded: list[str] = field(default_factory=list)             # "Arial,Bold"
    look_alikes: list[tuple[str, str]] = field(default_factory=list)  # ("Helvetica", "LiberationSans-Regular")
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (font name, plain reason)


def _number(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def embed_missing_fonts(pdf: Pdf, use_system_fonts: bool = True) -> EmbedResult:
    result = EmbedResult()
    done: set[str] = set()
    usage = used_codes(pdf)
    for font in all_fonts(pdf):
        if is_embedded(font):
            continue
        name = base_name(font) or "(unnamed font)"
        subtype = font.get("/Subtype")
        if subtype == Name.Type0:
            result.skipped.append((name, "composite fonts (for example Chinese or Japanese) need the original font file"))
            continue
        if subtype not in (Name.Type1, Name.TrueType, Name.MMType1):
            result.skipped.append((name, "this kind of font cannot be embedded automatically"))
            continue
        if any(symbol in name.lower().replace(" ", "") for symbol in _SYMBOL_FONTS):
            result.skipped.append((name, "symbol fonts need the original font file"))
            continue
        names = glyph_names(font)
        if names is None:
            result.skipped.append((name, "the font uses its own character set, which is unknown without the font file"))
            continue
        desc = descriptor(font)
        source = find_source(
            name, flags(font),
            _number(desc.get("/FontWeight")) if desc is not None else 0,
            _number(desc.get("/ItalicAngle")) if desc is not None else 0,
            use_system_fonts=use_system_fonts,
        )
        if source is None:
            result.skipped.append((name, "neither this font nor a free look-alike is available"))
            continue
        used = usage.get(font.objgen) if font.is_indirect else None
        reason = _embed(pdf, font, names, source, used)
        if reason is not None:
            result.skipped.append((name, reason))
            continue
        if name not in done:
            done.add(name)
            result.embedded.append(name)
            if not source.exact:
                result.look_alikes.append((name, source.postscript_name))
    return result


def _codes_and_widths(font: Dictionary, names: dict[int, str]) -> tuple[list[int], dict[int, float]]:
    widths = font.get("/Widths")
    first = font.get("/FirstChar")
    if isinstance(widths, Array) and first is not None:
        first = int(first)
        values = {first + i: _number(width) for i, width in enumerate(widths)}
        return [code for code in values if code in names], values
    return sorted(names), {}


def _encoding_for_truetype(font: Dictionary, names: dict[int, str]):
    """The Encoding entry a non-symbolic TrueType font needs (WinAnsi or MacRoman based)."""
    encoding = font.get("/Encoding")
    base = encoding.get("/BaseEncoding") if isinstance(encoding, Dictionary) else encoding
    if base in (Name.WinAnsiEncoding, Name.MacRomanEncoding):
        return encoding
    differences = Array()
    previous = None
    for code in sorted(names):
        if WIN_ANSI_ENCODING.get(code) == names[code]:
            continue
        if previous is None or code != previous + 1:
            differences.append(code)
        differences.append(Name("/" + names[code]))
        previous = code
    return Dictionary(Type=Name.Encoding, BaseEncoding=Name.WinAnsiEncoding, Differences=differences)


def _embed(pdf: Pdf, font: Dictionary, names: dict[int, str], source: FontSource,
           used: set[int] | None) -> str | None:
    codes, pdf_widths = _codes_and_widths(font, names)
    if used is not None:
        missing_names = sorted(code for code in used if code not in names or names[code] == ".notdef")
        if missing_names:
            return f"some characters it shows have no name in its encoding (codes {missing_names[:5]})"
        if pdf_widths and any(code not in pdf_widths for code in used):
            return "the file gives no width for some characters it shows"
    # All characters the encoding can show go into the font (it may also be used in places that
    # were not scanned, e.g. form field appearances); only the shown ones must be available.
    codes = sorted(set(codes) | {code for code in names if names[code] != ".notdef"})
    text_by_code = {code: unicode_of(names[code]) for code in codes}
    unknown = [names[code] for code, text in text_by_code.items()
               if not text and names[code] != ".notdef" and (used is None or code in used)]
    if unknown:
        return f"some characters have names that are not standard ({', '.join(unknown[:3])})"
    try:
        program = source.load()
    except Exception:
        return "the font file on this computer could not be read"
    available = program.getBestCmap() or {}
    lacking = [names[code] for code, text in text_by_code.items()
               if code in (used or ()) and (len(text) != 1 or ord(text) not in available)]
    if lacking:
        return f"the replacement font lacks characters this font shows ({', '.join(lacking[:3])})"
    wanted = {ord(text) for text in text_by_code.values() if len(text) == 1 and ord(text) in available}
    if not wanted:
        return "the available font has none of the characters this font uses"

    options = Options()
    options.layout_features = []
    options.notdef_outline = True
    options.recalc_bounds = True
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6]
    options.drop_tables += ["DSIG", "GDEF", "GPOS", "GSUB", "kern", "vhea", "vmtx", "morx", "feat"]
    subsetter = Subsetter(options=options)
    subsetter.populate(unicodes=sorted(wanted))
    subsetter.subset(program)

    cmap = program["cmap"]
    unicode_table = next((t for t in cmap.tables if (t.platformID, t.platEncID) == (3, 1)), None)
    if unicode_table is None:
        unicode_table = CmapSubtable.newSubtable(4)
        unicode_table.platformID, unicode_table.platEncID, unicode_table.language = 3, 1, 0
        unicode_table.cmap = dict(program.getBestCmap())
    cmap.tables = [unicode_table]                          # one Unicode table, as PDF/UA expects
    glyph_of = unicode_table.cmap

    units = program["head"].unitsPerEm
    hmtx = program["hmtx"]
    set_widths: dict[str, float] = {}
    for code in codes:
        text = text_by_code.get(code, "")
        glyph = glyph_of.get(ord(text)) if len(text) == 1 else None
        if glyph is None or code not in pdf_widths or glyph in set_widths:
            continue
        set_widths[glyph] = pdf_widths[code]
        hmtx[glyph] = (round(pdf_widths[code] * units / 1000), hmtx[glyph][1])

    buffer = io.BytesIO()
    program.save(buffer)
    data = buffer.getvalue()
    tag = "".join(chr(65 + byte % 26) for byte in hashlib.sha1(data).digest()[:6])
    font_name = f"{tag}+{base_name(font) if source.exact else source.postscript_name}"

    if not pdf_widths:                                      # standard 14 fonts may omit widths
        present = [code for code in codes if len(text_by_code[code]) == 1 and ord(text_by_code[code]) in glyph_of]
        first, last = min(present), max(present)
        widths = []
        for code in range(first, last + 1):
            glyph = glyph_of.get(ord(text_by_code[code])) if code in present else None
            widths.append(round(hmtx[glyph][0] * 1000 / units) if glyph else 0)
        font["/FirstChar"], font["/LastChar"] = first, last
        font["/Widths"] = pdf.make_indirect(Array(widths))

    font["/Encoding"] = _encoding_for_truetype(font, names)
    font["/Subtype"] = Name.TrueType
    font["/BaseFont"] = Name("/" + font_name)

    desc = own_descriptor(pdf, font)
    scale = 1000 / units
    head, hhea = program["head"], program["hhea"]
    os2 = program["OS/2"] if "OS/2" in program else None
    italic = float(program["post"].italicAngle) if "post" in program else 0.0
    new_flags = (flags(font) & ~FLAG_SYMBOLIC) | FLAG_NONSYMBOLIC
    if italic:
        new_flags |= FLAG_ITALIC
    desc["/FontName"] = Name("/" + font_name)
    desc["/Flags"] = new_flags
    desc["/FontBBox"] = Array([round(v * scale) for v in (head.xMin, head.yMin, head.xMax, head.yMax)])
    desc["/ItalicAngle"] = italic
    desc["/Ascent"] = round(hhea.ascent * scale)
    desc["/Descent"] = round(hhea.descent * scale)
    cap_height = getattr(os2, "sCapHeight", 0) if os2 is not None else 0
    desc["/CapHeight"] = round((cap_height or hhea.ascent) * scale)
    if "/StemV" not in desc:
        desc["/StemV"] = 120 if os2 is not None and os2.usWeightClass >= 600 else 80
    for key in ("/FontFile", "/FontFile3", "/CharSet", "/CIDSet"):
        if key in desc:
            del desc[key]
    stream = pdf.make_stream(data)
    stream["/Length1"] = len(data)
    desc["/FontFile2"] = stream
    return None
