"""Finding the fonts of a document and reading their encodings."""

from __future__ import annotations

import io
import re

from fontTools.agl import toUnicode
from fontTools.ttLib import TTFont
from pdfminer.latin_enc import ENCODING
from pikepdf import Array, Dictionary, Name, Pdf, Stream

STANDARD_ENCODING = {std: name for name, std, mac, win, pdf in ENCODING if std is not None}
MAC_ROMAN_ENCODING = {mac: name for name, std, mac, win, pdf in ENCODING if mac is not None}
WIN_ANSI_ENCODING = {win: name for name, std, mac, win, pdf in ENCODING if win is not None}
_BASE_ENCODINGS = {
    "/WinAnsiEncoding": WIN_ANSI_ENCODING,
    "/MacRomanEncoding": MAC_ROMAN_ENCODING,
    "/StandardEncoding": STANDARD_ENCODING,
}

FLAG_SYMBOLIC = 4
FLAG_NONSYMBOLIC = 32
FLAG_ITALIC = 64
FLAG_FORCE_BOLD = 1 << 18

_SUBSET_TAG = re.compile(r"^[A-Z]{6}\+")


def all_fonts(pdf: Pdf) -> list[Dictionary]:
    """Every font dictionary used on pages, in form XObjects, annotations and Type 3 fonts."""
    found: dict[tuple[int, int], Dictionary] = {}
    direct: list[Dictionary] = []
    seen: set[tuple[int, int]] = set()

    def visit_resources(resources) -> None:
        if not isinstance(resources, Dictionary):
            return
        if resources.is_indirect:
            if resources.objgen in seen:
                return
            seen.add(resources.objgen)
        fonts = resources.get("/Font")
        if isinstance(fonts, Dictionary):
            for _, font in fonts.items():
                if not isinstance(font, Dictionary):
                    continue
                if font.is_indirect:
                    if font.objgen not in found:
                        found[font.objgen] = font
                        visit_resources(font.get("/Resources"))         # Type 3 glyphs
                else:
                    direct.append(font)
        xobjects = resources.get("/XObject")
        if isinstance(xobjects, Dictionary):
            for _, xobject in xobjects.items():
                if isinstance(xobject, Stream) and xobject.get("/Subtype") == Name.Form:
                    if xobject.objgen in seen:
                        continue
                    seen.add(xobject.objgen)
                    visit_resources(xobject.get("/Resources"))

    for page in pdf.pages:
        visit_resources(page.obj.get("/Resources"))
        for annotation in page.obj.get("/Annots") or []:
            appearances = annotation.get("/AP") if isinstance(annotation, Dictionary) else None
            if not isinstance(appearances, Dictionary):
                continue
            for _, appearance in appearances.items():
                streams = [appearance] if isinstance(appearance, Stream) else (
                    [value for _, value in appearance.items()] if isinstance(appearance, Dictionary) else [])
                for stream in streams:
                    if isinstance(stream, Stream) and stream.objgen not in seen:
                        seen.add(stream.objgen)
                        visit_resources(stream.get("/Resources"))
    acroform = pdf.Root.get("/AcroForm")
    if isinstance(acroform, Dictionary):
        visit_resources(acroform.get("/DR"))
    return list(found.values()) + direct


def base_name(font: Dictionary) -> str:
    """The font's PostScript name without a subset tag ("ABCDEF+Arial-BoldMT" -> "Arial-BoldMT")."""
    from pdfaccessguru.utils.pdf_names import name_text

    return _SUBSET_TAG.sub("", name_text(font.get("/BaseFont", "")).lstrip("/"))


def descriptor(font: Dictionary) -> Dictionary | None:
    if font.get("/Subtype") == Name.Type0:
        descendants = font.get("/DescendantFonts")
        if isinstance(descendants, Array) and len(descendants) and isinstance(descendants[0], Dictionary):
            value = descendants[0].get("/FontDescriptor")
            return value if isinstance(value, Dictionary) else None
        return None
    value = font.get("/FontDescriptor")
    return value if isinstance(value, Dictionary) else None


def is_embedded(font: Dictionary) -> bool:
    if font.get("/Subtype") == Name.Type3:
        return True
    desc = descriptor(font)
    return desc is not None and any(key in desc for key in ("/FontFile", "/FontFile2", "/FontFile3"))


def flags(font: Dictionary) -> int:
    desc = descriptor(font)
    try:
        return int(desc.get("/Flags", 0)) if desc is not None else 0
    except (TypeError, ValueError):
        return 0


def glyph_names(font: Dictionary) -> dict[int, str] | None:
    """
    Code -> glyph name for a simple font, from its Encoding (named or with Differences).
    None if the encoding cannot be read without the (missing) font program, e.g. a symbolic
    font that uses its built-in encoding.
    """
    encoding = font.get("/Encoding")
    differences = None
    if isinstance(encoding, Dictionary):
        differences = encoding.get("/Differences")
        encoding = encoding.get("/BaseEncoding")
    if encoding is None:
        if flags(font) & FLAG_SYMBOLIC and not flags(font) & FLAG_NONSYMBOLIC and not _is_latin_text_font(font):
            return None
        names = dict(STANDARD_ENCODING)                       # built-in encoding of text fonts
    elif str(encoding) in _BASE_ENCODINGS:
        names = dict(_BASE_ENCODINGS[str(encoding)])
    else:
        return None
    if isinstance(differences, Array):
        code = None
        for item in differences:
            if isinstance(item, int):
                code = item
            elif isinstance(item, Name) and code is not None:
                names[code] = str(item).lstrip("/")
                code += 1
    return names


def _is_latin_text_font(font: Dictionary) -> bool:
    """Standard text fonts (Helvetica, Times, Courier, Arial ...) that are marked symbolic by mistake."""
    name = base_name(font).lower()
    return any(family in name for family in ("helvetica", "times", "courier", "arial"))


def unicode_of(glyph_name: str) -> str:
    """The Unicode text of an Adobe Glyph List name ('' if unknown)."""
    try:
        return toUnicode(glyph_name) or ""
    except Exception:
        return ""


def font_program(font: Dictionary) -> tuple[TTFont, str] | None:
    """The embedded TrueType/OpenType program and the descriptor key that holds it."""
    desc = descriptor(font)
    if desc is None:
        return None
    for key in ("/FontFile2", "/FontFile3"):
        stream = desc.get(key)
        if not isinstance(stream, Stream):
            continue
        if key == "/FontFile3" and stream.get("/Subtype") != Name.OpenType:
            continue
        try:
            return TTFont(io.BytesIO(stream.read_bytes())), key
        except Exception:
            return None
    return None


def store_program(pdf: Pdf, font: Dictionary, program: TTFont, key: str) -> None:
    """Write a changed font program back into the font's descriptor."""
    buffer = io.BytesIO()
    program.save(buffer)
    data = buffer.getvalue()
    desc = own_descriptor(pdf, font)
    old = desc.get(key)
    stream = pdf.make_stream(data)
    if key == "/FontFile2":
        stream["/Length1"] = len(data)
    elif isinstance(old, Stream) and "/Subtype" in old:
        stream["/Subtype"] = old["/Subtype"]
    desc[key] = stream


_FONT_IN_CONTEXT = re.compile(r"/font\[\d+\]\(([^)]*)\)|/usedGlyphs\[\d+\]\((\S+)")
_PAGE_IN_CONTEXT = re.compile(r"/pages\[(\d+)\]")


def find_font_in_context(context: str, pdf: Pdf) -> Dictionary | None:
    """
    The font dictionary a veraPDF context path names, e.g. ".../pages[0](12 0 obj PDPage)/
    contentStream[0](...)/operators[7]/font[0](UMBSME+AdobeGothicStd-Bold)". Fonts of the named
    page come first; fonts in form XObjects, annotations and other pages are found as well.
    """
    names = [font or glyph_font for font, glyph_font in _FONT_IN_CONTEXT.findall(context or "")]
    if not names:
        return None
    wanted = names[-1].strip()
    wanted_base = _SUBSET_TAG.sub("", wanted)
    candidates = all_fonts(pdf)
    page = _PAGE_IN_CONTEXT.search(context or "")
    if page is not None and int(page.group(1)) < len(pdf.pages):
        resources = pdf.pages[int(page.group(1))].obj.get("/Resources")
        fonts = resources.get("/Font") if isinstance(resources, Dictionary) else None
        if isinstance(fonts, Dictionary):
            candidates = [font for _, font in fonts.items() if isinstance(font, Dictionary)] + candidates
    for exact in (True, False):
        for font in candidates:
            from pdfaccessguru.utils.pdf_names import name_text

            name = name_text(font.get("/BaseFont", "")).lstrip("/")
            if (name == wanted) if exact else (base_name(font) == wanted_base):
                return font
    return None


_SHOW_TEXT = {"Tj", "'", '"', "TJ"}


def used_codes(pdf: Pdf) -> dict[tuple[int, int], set[int]]:
    """
    Character codes each font actually shows (CIDs for Identity-encoded composite fonts), from
    the text operators of all pages and form XObjects (key: the font's object number). Fonts not found here may still be used
    elsewhere (e.g. in annotation appearances), so callers treat a missing entry as "unknown".
    """
    from pikepdf import parse_content_stream

    codes: dict[tuple[int, int], set[int]] = {}
    seen: set[tuple[int, int]] = set()

    def scan(owner, resources) -> None:
        fonts = resources.get("/Font") if isinstance(resources, Dictionary) else None
        xobjects = resources.get("/XObject") if isinstance(resources, Dictionary) else None
        try:
            operations = parse_content_stream(owner)
        except Exception:
            return
        current = None
        for operands, operator in operations:
            name = str(operator)
            if name == "Tf" and operands and isinstance(fonts, Dictionary):
                font = fonts.get(str(operands[0]))
                current = font if isinstance(font, Dictionary) and font.is_indirect else None
            elif name in _SHOW_TEXT and current is not None:
                two_byte = current.get("/Subtype") == Name.Type0
                if two_byte and current.get("/Encoding") not in (Name("/Identity-H"), Name("/Identity-V")):
                    continue                                   # other CMaps: codes are not CIDs
                target = codes.setdefault(current.objgen, set())
                for operand in operands:
                    items = list(operand) if isinstance(operand, Array) else [operand]
                    for item in items:
                        if isinstance(item, (int, float)) or not hasattr(item, "__bytes__"):
                            continue
                        try:
                            data = bytes(item)
                        except Exception:
                            continue
                        if two_byte:
                            target.update(data[i] << 8 | data[i + 1] for i in range(0, len(data) - 1, 2))
                        else:
                            target.update(data)
            elif name == "Do" and operands and isinstance(xobjects, Dictionary):
                xobject = xobjects.get(str(operands[0]))
                if isinstance(xobject, Stream) and xobject.get("/Subtype") == Name.Form and xobject.objgen not in seen:
                    seen.add(xobject.objgen)
                    scan(xobject, xobject.get("/Resources") or resources)

    for page in pdf.pages:
        scan(page, page.obj.get("/Resources"))
    return codes


def own_descriptor(pdf: Pdf, font: Dictionary) -> Dictionary:
    """
    The font's descriptor, copied first if other fonts share it: a font program added or
    changed for this font must not change the fonts it shares the descriptor with.
    """
    holder = font
    if font.get("/Subtype") == Name.Type0:
        holder = font["/DescendantFonts"][0]
    desc = holder.get("/FontDescriptor")
    if not isinstance(desc, Dictionary):
        desc = pdf.make_indirect(Dictionary(Type=Name.FontDescriptor))
        holder["/FontDescriptor"] = desc
        return desc
    sharing = sum(1 for other in all_fonts(pdf)
                  if other is not font and descriptor(other) is not None and desc.is_indirect
                  and descriptor(other).is_indirect and descriptor(other).objgen == desc.objgen
                  and not (other.is_indirect and font.is_indirect and other.objgen == font.objgen))
    if sharing:
        desc = pdf.make_indirect(Dictionary({key: value for key, value in desc.items()}))
        holder["/FontDescriptor"] = desc
    return desc
