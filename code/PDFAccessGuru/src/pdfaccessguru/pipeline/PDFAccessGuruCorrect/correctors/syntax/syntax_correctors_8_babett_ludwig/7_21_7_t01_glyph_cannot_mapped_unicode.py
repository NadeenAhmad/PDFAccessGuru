import io
from io import BytesIO
import re

from fontTools.agl import toUnicode
from fontTools.ttLib import TTFont
import pikepdf
from pikepdf import Dictionary, Name, Pdf, parse_content_stream

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_debug

from pdfaccessguru.pipeline.reporting.writer import report_review


def _debug_print(*_args, **_kwargs) -> None:
    """Debug output was printed to the user's console; it is dropped (Phase 5)."""


@corrector("glyph-cannot-mapped-unicode")
def correct_glyph_cannot_mapped_unicode(
    detected_violation: DetectedViolation,
    pdf: Pdf,
):
    """Resolves unmapped PDF glyph violations by inspecting the content stream, resolving character metadata across Type0 or simple font definitions, attempting Adobe Glyph List mapping or LLM-assisted inference, and persisting the resulting mapping into a new or updated /ToUnicode CMap stream."""
    #print("IM Corrector 7.21.7.01")
    page, operator_index, cid_index, font = (
        detected_violation.supplementary_information
    )

    operators = parse_content_stream(page)
    instruction = operators[operator_index]

    byte_length = get_character_byte_length(font)

    glyph_bytes, character_code = get_glyph_code_from_operator(
        instruction, cid_index, byte_length
    )
    _debug_print("Character code:", character_code)

    if character_code is None:
        raise CouldNotCorrectDetectedViolationException(
            "No character code found"
        )

    glyph_information = resolve_character(font, character_code)

    _debug_print("Glyph information:")
    _debug_print(glyph_information)

    unicode_result = resolve_unicode(
        glyph_information, font, glyph_bytes, detected_violation
    )

    _debug_print("Unicode result:")
    _debug_print(unicode_result)

    if unicode_result is None:
        raise CouldNotCorrectDetectedViolationException(
            f"glyph-cannot-mapped-unicode: no reliable Unicode value for character code {character_code}; "
            "it is not mapped to a space because that would change the text read by screen readers"
        )

    if unicode_result:
        update_or_create_tounicode(
            pdf, font, character_code, unicode_result, byte_length
        )

def get_glyph_code_from_operator(operator, glyph_index, byte_length):
    """Extracts the raw byte sequence and integer decimal value for the nth glyph in a PDF text operator (TJ/Tj)."""
    glyph_counter = 0

    for operand in operator.operands:
        if isinstance(operand, pikepdf.Array):
            items = operand
        else:
            items = [operand]

        for item in items:
            if isinstance(item, pikepdf.String):
                data = bytes(item)
                _debug_print("all data ", data)
                _debug_print("BYTES:", data.hex())

                for i in range(0, len(data), byte_length):
                    glyph_bytes = data[i : i + byte_length]

                    if len(glyph_bytes) < byte_length:
                        continue

                    if glyph_counter == glyph_index:
                        _debug_print("glyph_bytes ", glyph_bytes)
                        glyph_decimal = int.from_bytes(
                            glyph_bytes, byteorder="big"
                        )
                        return glyph_bytes, glyph_decimal

                    glyph_counter += 1

    return None


def get_character_byte_length(font):
    """Determines the expected byte length of character codes based on the PDF font subtype and encoding (1 byte for simple fonts, 2 bytes for 2-byte Type0 encodings)."""
    subtype = font.get("/Subtype")

    if subtype != "/Type0":
        return 1

    encoding = font.get("/Encoding")

    if encoding in ["/Identity-H", "/Identity-V"]:
        return 2




def resolve_character(pdf_font, character_code):
    """Dispatches character resolution based on font subtype to retrieve CID/GID mappings for Type0 fonts or glyph names for simple fonts."""
    subtype = pdf_font.get("/Subtype")

    if subtype == "/Type0":
        return resolve_type0_font(pdf_font, character_code)
    else:
        return resolve_simple_font(pdf_font, character_code)


def resolve_unicode(
    glyph_information, font, glyph_bytes, detected_violation
):
    """Determines the final Unicode representation for a resolved glyph, utilizing AGL/LLM fallbacks for simple fonts or TrueType cmap lookups for Type0 fonts."""
    if glyph_information is None:
        return None

    glyph_type = glyph_information.get("type")

    if glyph_type == "Simple":
        unicode_char = resolve_simplefont_unicode_with_fallback(
            glyph_information, font, glyph_bytes, detected_violation
        )
        return unicode_char

    elif glyph_type == "Type0":
        gid = glyph_information.get("gid")
        unicode_char = resolve_type0_gid_unicode(font, gid)

        if unicode_char:
            return unicode_char

        return None

    return None


def resolve_type0_gid_unicode(font, gid):
    """Retrieves the corresponding Unicode codepoint for a Type0 font's Glyph ID (GID) by parsing its descendant TrueType font's internal cmap table."""
    descendants = font.get("/DescendantFonts")

    if not descendants:
        return None

    cid_font = descendants[0]

    descriptor = cid_font.get("/FontDescriptor")

    if not descriptor:
        return None

    font_stream = descriptor.get("/FontFile2") or descriptor.get(
        "/FontFile3"
    )

    if not font_stream:
        return None

    try:
        font_bytes = font_stream.read_bytes()
        ttf = TTFont(BytesIO(font_bytes))
        glyph_order = ttf.getGlyphOrder()

        if gid >= len(glyph_order):
            return None

        glyph_name = glyph_order[gid]

        for cmap in ttf["cmap"].tables:
            if cmap.isUnicode():
                for uni, name in cmap.cmap.items():
                    if name == glyph_name:
                        return f"U+{uni:04X}"

    except Exception as e:
        _debug_print("Font parsing failed:", e)

    return None


def resolve_simple_font(font, code):
    """Constructs a dictionary containing simple font metadata and the resolved glyph name for a given character code."""
    glyph_name = resolve_glyph_name(font, code)

    return {"type": "Simple", "code": code, "glyph_name": glyph_name}


def resolve_glyph_name(font, code):
    """Extracts the glyph name corresponding to a character code by parsing the font's /Encoding /Differences array."""
    encoding = font.get("/Encoding")

    if not encoding:
        return None

    differences = encoding.get("/Differences")

    if not differences:
        return None

    current = 0

    for item in differences:
        if isinstance(item, int):
            current = item
        else:
            name = str(item)
            if name.startswith("/"):
                name = name[1:]

            if current == code:
                return name

            current += 1

    return None


def glyphname_to_unicode_agl(glyph_name: str):
    """Attempts to translate a glyph name directly into a Unicode string using the Adobe Glyph List (AGL)."""
    if not glyph_name:
        return None

    uni = toUnicode(glyph_name)
    if uni:
        return uni

    return None


def unicode_from_font_program(pdf_font, code) -> str | None:
    """
    The Unicode value the embedded TrueType program itself gives for the glyph that the code
    shows (its own character table, read backwards). Exact and needs no AI. Private-use values
    (U+E000 to U+F8FF) are not real characters and are ignored.
    """
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.fonts import font_program, glyph_names
    from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.font_repair.programs import glyph_for_code

    try:
        loaded = font_program(pdf_font)
        if loaded is None or "cmap" not in loaded[0]:
            return None
        program = loaded[0]
        glyph = glyph_for_code(program, pdf_font, int(code), glyph_names(pdf_font))
        if not glyph or glyph == ".notdef":
            return None
        for table in program["cmap"].tables:
            if (table.platformID, table.platEncID) not in ((3, 1), (3, 10), (0, 3), (0, 4)):
                continue
            for value, name in sorted(table.cmap.items()):
                if name == glyph and not 0xE000 <= value <= 0xF8FF and (value != 0x20 or glyph == "space"):
                    return f"U+{value:04X}"
    except Exception:
        return None
    return None


def resolve_simplefont_unicode_with_fallback(
    resolve_result, pdf_font, glyph_bytes, detected_violation
):
    """Attempts to resolve a simple font glyph's Unicode value using AGL, falling back to an LLM prompt if unmapped, and validates the output structure."""
    glyph_name = resolve_result.get("glyph_name")
    code = resolve_result.get("code")

    unicode_char = glyphname_to_unicode_agl(glyph_name) or unicode_from_font_program(pdf_font, code)

    from pdfaccessguru.LLM.fallback import ai_available, note_fallback

    if not unicode_char and not ai_available():
        note_fallback("unicode")
        return None
    if not unicode_char:
        unicode_char = None
        try:
            system_prompt, user_prompt = (
                build_prompt_resolve_glyph_unicode(
                    glyph_decimal=code,
                    glyph_name=glyph_name,
                    glyph_bytes=glyph_bytes,
                    detected_violation=detected_violation,
                )
            )

            provider = OpenRouterBaseProvider()
            response = provider.send_message(system_prompt, user_prompt)

            _debug_print("response LLM:", repr(response))

            if response:
                response = response.strip()

                if re.fullmatch(r"U\+[0-9A-Fa-f]{4,6}", response) and response.upper() != "U+0020":
                    unicode_char = response.upper()
                    report_review(
                        f"Character code {code} (glyph {glyph_name!r}) was mapped to {unicode_char} by a language model. Please check the text."
                    )
                else:
                    _debug_print("Invalid LLM response:", repr(response))

        except Exception as e:
            _debug_print("LLM ERROR:", repr(e))

        if not unicode_char:
            return None

    if not re.fullmatch(r"U\+[0-9A-Fa-f]{4,6}", unicode_char):
        _debug_print("Invalid Unicode structure:", repr(unicode_char))
        return None

    try:
        codepoint = int(unicode_char[2:], 16)

        if codepoint > 0x10FFFF:
            _debug_print("Unicode codepoint too large:", unicode_char)
            return None

        if 0xD800 <= codepoint <= 0xDFFF:
            _debug_print("Unicode surrogate:", unicode_char)
            return None

    except (ValueError, TypeError):
        _debug_print("Invalid Unicode codepoint:", repr(unicode_char))
        return None

    return unicode_char.upper()


def build_prompt_resolve_glyph_unicode(
    glyph_decimal, glyph_name, glyph_bytes, detected_violation
):
    """Constructs system and user prompts to query an LLM for inferring the semantic Unicode representation of an ambiguous glyph."""
    system_prompt = """
You are an expert in PDF fonts, glyph names, character codes,
glyph bytes, and Unicode mapping.

Task:
Determine the correct Unicode character represented by a PDF glyph.

Use ALL available glyph information together:

1. Glyph name
2. Glyph bytes
3. Character code

The glyph name is the primary semantic source of information.
The glyph bytes are an additional important source of information
and should be considered when determining the Unicode character.

Rules:

- Determine the semantic Unicode character represented by the glyph.
- Prefer the meaning of the glyph name according to Adobe Glyph List
  conventions and known font naming conventions.
- ALSO examine the actual glyph bytes and use them as supporting
  evidence when determining the Unicode character.
- The glyph bytes may help distinguish between possible interpretations
  of the glyph name or confirm the character represented by the glyph.
- Do not simply convert the character code or glyph bytes directly
  into a Unicode code point.
- Do not assume that the numeric value of the glyph bytes represents
  the Unicode value.
- If the available information is ambiguous, contradictory, incomplete,
  or no reliable Unicode character can be determined, return UNKNOWN
  (space).
- Never guess a Unicode character.

Output:
- Return ONLY the Unicode code point.
- Use the format:
  U+XXXX

If no reliable Unicode mapping can be determined, return:
UNKNOWN
"""

    user_prompt = f"""
PDF/UA violation:
{detected_violation}

Glyph information:

Character code (decimal):
{glyph_decimal}

Glyph bytes:
{glyph_bytes}

Glyph name:
{glyph_name}

Task:

Determine the semantic Unicode code point represented by this glyph.

Consider the glyph name as the primary semantic information and
use the actual glyph bytes as additional evidence.

The character code and glyph bytes must NOT be interpreted as the
Unicode value directly. Use them only to help identify or validate
the glyph.

Return only:
U+XXXX

If no reliable Unicode mapping exists or you are not sufficiently
certain, return:
UNKNOWN
"""

    return system_prompt, user_prompt


def resolve_type0_font(font, cid):
    """Resolves a Type0 font character ID (CID) to its corresponding Glyph ID (GID) using Identity mapping or a /CIDToGIDMap stream if available."""
    encoding = font.get("/Encoding")

    if encoding in ["/Identity-H", "/Identity-V"]:
        return {"type": "Type0", "cid": cid, "gid": cid}

    descendants = font.get("/DescendantFonts")

    if not descendants:
        return None

    cid_font = descendants[0]
    cid_to_gid = cid_font.get("/CIDToGIDMap")

    if cid_to_gid:
        gid = cid_to_gid_lookup(cid_to_gid, cid)
        return {"type": "Type0", "cid": cid, "gid": gid}

    return {"type": "Type0", "cid": cid, "gid": cid}


def cid_to_gid_lookup(stream, cid):
    """Reads a binary /CIDToGIDMap stream and performs a 2-byte offset lookup to find the GID corresponding to a given CID."""
    data = stream.read_bytes()
    offset = cid * 2

    if offset + 2 > len(data):
        return -1

    return int.from_bytes(data[offset : offset + 2], "big")


def update_or_create_tounicode(
    pdf,
    font,
    character_code,
    unicode_value,
    byte_length,
):
    """Appends a new character-to-Unicode mapping to an existing /ToUnicode stream, or generates and attaches a new /ToUnicode stream if none exists."""
    existing_tounicode = font.get("/ToUnicode")

    if existing_tounicode:
        _debug_print("Existing ToUnicode found")
        return add_missing_tounicode_mapping(
            font, character_code, unicode_value, byte_length
        )

    _debug_print("Creating new ToUnicode")
    cmap_bytes = create_tounicode_cmap(
        character_code, unicode_value, byte_length
    )

    stream = pdf.make_stream(cmap_bytes)
    font["/ToUnicode"] = stream

    return True


def create_tounicode_cmap(
    character_code: int, unicode_value: str, byte_length: int
):
    """Generates the raw PostScript bytes for a basic /ToUnicode CMap stream with a single bfchar mapping."""
    unicode_hex = unicode_value.replace("U+", "").upper()

    if byte_length == 2:
        code_hex = f"{character_code:04X}"
        codespace_start = "<0000>"
        codespace_end = "<FFFF>"
    else:
        code_hex = f"{character_code:02X}"
        codespace_start = "<00>"
        codespace_end = "<FF>"

    cmap = f"""
/CIDInit /ProcSet findresource begin
12 dict begin
begincmap

/CMapName /CustomToUnicode def
/CMapType 2 def

1 begincodespacerange
{codespace_start}{codespace_end}
endcodespacerange

1 beginbfchar
<{code_hex}><{unicode_hex}>
endbfchar

endcmap
CMapName currentdict /CMap defineresource pop
end
end
"""

    return cmap.encode("latin1")


def add_missing_tounicode_mapping(
    font, character_code: int, unicode_value: str, byte_length: int
):
    """Parses an existing /ToUnicode PostScript CMap stream text and injects a new character mapping into the bfchar block while updating its count header."""
    to_unicode = font.get("/ToUnicode")

    if not to_unicode:
        _debug_print("No ToUnicode stream available")
        return False

    cmap = to_unicode.read_bytes().decode("latin1")

    unicode_hex = unicode_value.replace("U+", "").upper()

    if byte_length == 2:
        glyph_hex = f"{character_code:04X}"
    else:
        glyph_hex = f"{character_code:02X}"

    new_mapping = f"<{glyph_hex}><{unicode_hex}>"

    _debug_print("Adding mapping:", new_mapping)

    if f"<{glyph_hex}>" in cmap:
        _debug_print("Mapping already exists")
        return False

    bfchar_match = re.search(r"(\d+)\s+beginbfchar", cmap)

    if bfchar_match:
        count = int(bfchar_match.group(1))
        new_count = count + 1

        _debug_print(f"Updating bfchar count: {count} -> {new_count}")

        cmap = (
            cmap[: bfchar_match.start(1)]
            + str(new_count)
            + cmap[bfchar_match.end(1) :]
        )

        insert_position = cmap.find("endbfchar")

        if insert_position == -1:
            return False

        cmap = (
            cmap[:insert_position]
            + new_mapping
            + "\n"
            + cmap[insert_position:]
        )

    else:
        cmap += (
            "\n1 beginbfchar\n"
            + new_mapping
            + "\n"
            + "endbfchar\n"
        )

    to_unicode.write(cmap.encode("latin1"))

    return True