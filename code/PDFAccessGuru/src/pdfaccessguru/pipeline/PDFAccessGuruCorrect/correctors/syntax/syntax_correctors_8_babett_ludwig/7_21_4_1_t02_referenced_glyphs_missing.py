from pathlib import Path
import io
import re

from fontTools.agl import toUnicode as agl_to_unicode
from fontTools.encodings.StandardEncoding import StandardEncoding
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from pikepdf import Array, Dictionary, Name, Pdf, parse_content_stream

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting import report_debug


BASE_DIR = Path(__file__).resolve().parent
FONTS_DIR = BASE_DIR / "fonts"
FONT_POOL_PATHS = list(FONTS_DIR.glob("*.ttf"))
loaded_fonts = [(str(path), TTFont(path)) for path in FONT_POOL_PATHS]


@corrector("referenced-glyphs-missing")
def correct_referenced_glyphs_missing(detected_violation, pdf):
    """
    Corrects missing glyphs or a missing embedded font program.

    The supplementary information provides the affected font together
    with the character codes that are actually used in the PDF. Simple
    fonts are handled by rebuilding their embedded TrueType font and
    updating the corresponding font dictionary.

    For Type0 fonts, the existing ToUnicode CMap is used to determine
    the required Unicode characters. A suitable font from the local
    font pool is then selected, subsetted, and embedded into the
    descendant CID font. The ToUnicode mapping is rebuilt so that the
    repaired font continues to map the PDF character codes correctly.
    """

    font, used_codes = detected_violation.supplementary_information

    subtype = font.get("/Subtype")

    if subtype != Name.Type0:
        fix_simple_font_embedding(pdf, font, used_codes)
        return

    descendant = font["/DescendantFonts"][0]

    tounicode = font.get("/ToUnicode")
    if not tounicode:
        return

    cmap = parse_tounicode_cmap_stream(bytes(tounicode.read_bytes()))

    used_codes = {c for c in used_codes if c in cmap}

    if not used_codes:
        return

    required_unicodes = {ord(cmap[c]) for c in used_codes}

    source_font = select_best_font_source_for_unicode_set(required_unicodes)

    font_bytes, subset_font = build_font_subset(source_font, required_unicodes)

    fontfile_stream = pdf.make_stream(font_bytes)
    fontfile_stream.Length1 = len(font_bytes)

    descriptor = descendant.get("/FontDescriptor")

    if descriptor:
        descriptor["/FontFile2"] = fontfile_stream

    code_to_unicode = {c: ord(cmap[c]) for c in used_codes}
    new_tounicode = build_tounicode_cmap_stream(pdf, code_to_unicode)

    font["/ToUnicode"] = new_tounicode


def fix_simple_font_embedding(pdf, font, used_codes):
    """
    Rebuilds the embedded font program for a simple Type1/TrueType font.

    The function first resolves the PDF character codes to Unicode
    characters and determines which characters are actually required.
    A suitable source font is selected from the local font pool and
    subsetted to those Unicode characters.

    The generated font is then embedded as FontFile2. Font metrics,
    character ranges, widths, the FontDescriptor, and the ToUnicode
    mapping are updated so that the repaired font can be used with the
    original PDF character codes.
    """

    code_to_unicode = map_simple_font_code_to_unicode(font)

    used_codes = {c for c in used_codes if c in code_to_unicode} or set(code_to_unicode)
    required_unicodes = {code_to_unicode[c] for c in used_codes}

    source_font = select_best_font_source_for_unicode_set(required_unicodes)

    font_bytes, subset_font = build_font_subset(source_font, required_unicodes)

    scale = 1000.0 / subset_font["head"].unitsPerEm
    cmap = subset_font.getBestCmap()

    first = min(used_codes)
    last = max(used_codes)

    widths = []

    for code in range(first, last + 1):
        uni = code_to_unicode.get(code)
        glyph = cmap.get(uni) if uni else None

        widths.append(
            round(subset_font["hmtx"][glyph][0] * scale)
            if glyph
            else 0
        )

    fontfile_stream = pdf.make_stream(font_bytes)
    fontfile_stream.Length1 = len(font_bytes)

    descriptor = pdf.make_indirect(
        Dictionary(
            Type=Name.FontDescriptor,
            FontName=font.get("/BaseFont", Name("/Helvetica")),
            Flags=32,
            FontBBox=Array(
                [
                    round(subset_font["head"].xMin * scale),
                    round(subset_font["head"].yMin * scale),
                    round(subset_font["head"].xMax * scale),
                    round(subset_font["head"].yMax * scale),
                ]
            ),
            ItalicAngle=0,
            Ascent=round(subset_font["hhea"].ascent * scale),
            Descent=round(subset_font["hhea"].descent * scale),
            CapHeight=round(
                getattr(
                    subset_font.get("OS/2"),
                    "sCapHeight",
                    subset_font["hhea"].ascent,
                )
                * scale
            ),
            StemV=88,
            FontFile2=pdf.make_indirect(fontfile_stream),
        )
    )

    font.Subtype = Name.TrueType
    font.FirstChar = first
    font.LastChar = last
    font.Widths = pdf.make_indirect(Array(widths))
    font.FontDescriptor = descriptor
    font.ToUnicode = build_tounicode_cmap_stream(
        pdf,
        {c: code_to_unicode[c] for c in used_codes},
    )

    if "/Encoding" not in font:
        font.Encoding = Name.WinAnsiEncoding

    return str(source_font).split("/")[-1], len(required_unicodes)


def fix_composite_font_embedding(pdf, font, used_codes):
    """
    Rebuilds the embedded font data of a composite Type0 font.

    The existing ToUnicode CMap is parsed to determine the Unicode
    characters represented by the used character codes. A suitable
    source font is selected and subsetted to those characters.

    The resulting subset is embedded into the descendant CID font.
    A new CIDToGIDMap and width information are generated so that
    the original character codes continue to reference the correct
    glyphs in the newly embedded font.
    """

    cid_font = font.DescendantFonts[0]

    existing_cmap = (
        parse_tounicode_cmap_stream(bytes(font.ToUnicode.read_bytes()))
        if "/ToUnicode" in font
        else {}
    )

    used_codes = {c for c in used_codes if c in existing_cmap} or set(existing_cmap)

    needed_mapping = {
        c: ord(existing_cmap[c][0])
        for c in used_codes
        if existing_cmap.get(c)
    }

    required_unicodes = set(needed_mapping.values())

    source_font = select_best_font_source_for_unicode_set(required_unicodes)

    font_bytes, subset_font = build_font_subset(source_font, required_unicodes)

    scale = 1000.0 / subset_font["head"].unitsPerEm
    cmap = subset_font.getBestCmap()

    max_code = max(needed_mapping)
    cid_to_gid = bytearray((max_code + 1) * 2)
    widths = Array()

    for code, uni in sorted(needed_mapping.items()):
        glyph_name = cmap.get(uni)
        if not glyph_name:
            continue

        glyph_id = subset_font.getGlyphID(glyph_name)

        cid_to_gid[code * 2:code * 2 + 2] = glyph_id.to_bytes(2, "big")

        widths.append(code)
        widths.append(
            Array(
                [round(subset_font["hmtx"][glyph_name][0] * scale)]
            )
        )

    fontfile_stream = pdf.make_stream(font_bytes)
    fontfile_stream.Length1 = len(font_bytes)

    cid_font.FontDescriptor.FontFile2 = pdf.make_indirect(fontfile_stream)
    cid_font.CIDToGIDMap = pdf.make_stream(bytes(cid_to_gid))
    cid_font.W = widths

    return str(source_font).split("/")[-1], len(required_unicodes)


def map_simple_font_code_to_unicode(font_object):
    """
    Builds the complete character-code-to-Unicode mapping for a simple
    PDF font.

    The PDF font encoding is resolved using its base encoding
    (WinAnsiEncoding, MacRomanEncoding, or StandardEncoding). If the
    font contains a /Differences array, those glyph names override the
    corresponding base encoding entries.

    The resulting mapping is used by the font repair logic to determine
    which Unicode characters have to be present in the replacement font.
    """

    encoding = font_object.get("/Encoding")

    base_decoder = decode_winansi
    differences_override = {}

    if isinstance(encoding, Name):
        base_decoder = BASE_ENCODING_MAP.get(
            str(encoding),
            decode_winansi,
        )

    elif isinstance(encoding, Dictionary):
        base_decoder = BASE_ENCODING_MAP.get(
            str(encoding.get("/BaseEncoding", "/StandardEncoding")),
            decode_standard_encoding,
        )

        diff_array = encoding.get("/Differences")

        if diff_array is not None:
            code = 0

            for item in diff_array:
                if isinstance(item, int):
                    code = int(item)
                else:
                    differences_override[code] = str(item)
                    code += 1

    output_mapping = {}

    for code in range(256):
        if code in differences_override:
            uni = glyph_name_to_unicode(differences_override[code])
        else:
            uni = base_decoder(code)

        if uni:
            output_mapping[code] = uni

    return output_mapping


def decode_winansi(byte):
    """
    Decodes a PDF character code using the WinAnsi/cp1252 encoding.

    Returns the corresponding Unicode codepoint or None if the byte
    cannot be decoded.
    """

    try:
        return ord(bytes([byte]).decode("cp1252"))
    except Exception:
        return None


def decode_macroman(byte):
    """
    Decodes a PDF character code using the MacRoman encoding.

    Returns the corresponding Unicode codepoint or None if the byte
    cannot be decoded.
    """

    try:
        return ord(bytes([byte]).decode("mac_roman"))
    except Exception:
        return None


def decode_standard_encoding(byte):
    """
    Converts a character code from PDF StandardEncoding to a Unicode
    codepoint by resolving its glyph name through the Adobe Glyph List.
    """

    glyph_name = (
        StandardEncoding[byte]
        if byte < len(StandardEncoding)
        else ".notdef"
    )

    return glyph_name_to_unicode(glyph_name)


BASE_ENCODING_MAP = {
    "/WinAnsiEncoding": decode_winansi,
    "/MacRomanEncoding": decode_macroman,
    "/StandardEncoding": decode_standard_encoding,
}


def glyph_name_to_unicode(name):
    """
    Converts an Adobe Glyph List glyph name into its Unicode codepoint.

    PDF font encodings commonly use names such as /A, /adieresis, or
    /uni20AC. The leading slash is removed before resolving the glyph
    name. Unresolvable names and .notdef return None.
    """

    if not name:
        return None

    name = name.lstrip("/")

    if name == ".notdef":
        return None

    unicode_char = agl_to_unicode(name)

    return ord(unicode_char[0]) if unicode_char else None


def select_best_font_source_for_unicode_set(required_unicodes):
    """
    Selects the font from the local font pool that provides the largest
    coverage of the required Unicode characters.

    Each loaded font exposes its supported Unicode characters through
    getBestCmap(). The font whose cmap contains the largest intersection
    with required_unicodes is selected as the source for the replacement
    font.
    """

    best_font_path = None
    best_coverage_score = -1

    for path, font in loaded_fonts:
        available_cmap = set(font.getBestCmap())
        coverage = len(required_unicodes & available_cmap)

        if coverage > best_coverage_score:
            best_font_path = path
            best_coverage_score = coverage

    return best_font_path


def build_font_subset(source_font_path, required_unicodes):
    """
    Creates a TrueType subset containing only the required Unicode
    characters.

    The source font is loaded, configured for subsetting, and reduced to
    the requested Unicode set. The resulting font is returned both as
    serialized bytes, which can be embedded into the PDF, and as a
    TTFont object, which is used to calculate metrics such as glyph
    widths and font bounds.
    """

    font = TTFont(source_font_path)

    options = Options()
    options.set(
        notdef_outline=True,
        recalc_bounds=True,
        glyph_names=True,
    )

    subsetter = Subsetter(options=options)
    subsetter.populate(unicodes=sorted(required_unicodes))
    subsetter.subset(font)

    buffer = io.BytesIO()
    font.save(buffer)

    return buffer.getvalue(), font


def build_tounicode_cmap_stream(pdf, code_to_unicode):
    """
    Builds a PDF ToUnicode CMap stream from a character-code mapping.

    Each PDF character code is mapped to its corresponding Unicode
    codepoint. The generated CMap is embedded as a PDF stream so that
    text extraction and character semantics remain consistent with the
    repaired font.
    """

    lines = []

    for code, uni in sorted(code_to_unicode.items()):
        hex_unicode = f"{uni:04X}" if uni <= 0xFFFF else None

        if hex_unicode is None:
            continue

        lines.append(f"<{code:02X}> <{hex_unicode}>")

    body = "\n".join(
        f"1 beginbfchar\n{line}\nendbfchar"
        for line in lines
    )

    cmap = (
        "/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
        "/CIDSystemInfo <</Registry(Adobe)/Ordering(UCS)/Supplement 0>> def\n"
        "/CMapName /Adobe-Identity-UCS def /CMapType 2 def\n"
        "1 begincodespacerange <00> <FFFF> endcodespacerange\n"
        f"{body}\n"
        "endcmap CMapName currentdict /CMap defineresource pop end end"
    )

    return pdf.make_stream(cmap.encode("latin-1"))


def parse_tounicode_cmap_stream(stream_bytes):
    """
    Parses a PDF ToUnicode CMap stream into a character-code-to-Unicode
    mapping.

    Both individual bfchar mappings and bfrange mappings are supported.
    The resulting dictionary uses the PDF character code as its key and
    the decoded Unicode character as its value, allowing the repair
    logic to determine which Unicode characters are represented by the
    composite font.
    """

    text = stream_bytes.decode("latin-1")
    result = {}

    for block in re.findall(r"beginbfchar(.*?)endbfchar", text, re.S):
        for src, dst in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>",
            block,
        ):
            decoded = bytes.fromhex(
                dst if len(dst) % 2 == 0 else "0" + dst
            )
            result[int(src, 16)] = decoded.decode("utf-16-be")

    for block in re.findall(r"beginbfrange(.*?)endbfrange", text, re.S):
        for lo, hi, start in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>",
            block,
        ):
            lo, hi = int(lo, 16), int(hi, 16)
            base = int(start, 16)

            for i, code in enumerate(range(lo, hi + 1)):
                result[code] = chr(base + i)

    return result

