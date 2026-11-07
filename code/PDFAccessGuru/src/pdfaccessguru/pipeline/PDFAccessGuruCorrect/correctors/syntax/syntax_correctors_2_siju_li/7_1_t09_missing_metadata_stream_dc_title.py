import re
from pathlib import Path
from xml.sax.saxutils import escape

from pikepdf import Pdf
from lxml import etree

import pikepdf

from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.LLM.output_checks import clean_llm_text, is_unusable_llm_text
from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.pipeline.reporting.writer import report_review
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.syntax.syntax_correctors_2_siju_li.language_utils import (
    extract_text_from_page,
)

MAX_TITLE_SOURCE_LENGTH = 3000
FALLBACK_TITLE = "Untitled Document"

_XML_UNSAFE_CHARS = re.compile(
    "[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD\U00010000-\U0010FFFF]"
)

# Debug-Flag: auf False setzen, sobald der Corrector zuverlässig läuft
_DEBUG = False


def _sanitize_for_xmp(text: str) -> str:
    cleaned = _XML_UNSAFE_CHARS.sub("", text)
    return cleaned.strip()


def _merge_duplicate_descriptions(root, ns):
    """
    RDF erlaubt technisch mehrere rdf:Description-Bl\u00f6cke mit demselben
    rdf:about (Properties werden logisch gemerged), aber strenge PDF/UA-Validatoren
    wie veraPDF pr\u00fcfen oft nur einen der Bl\u00f6cke - typischerweise den, der
    zuletzt im Dokument steht. Deshalb: alle Bl\u00f6cke mit gleichem about zu
    einem einzigen zusammenf\u00fchren, statt sie nebeneinander stehen zu lassen.
    """
    all_descriptions = root.findall(".//rdf:Description", ns)
    by_about: dict[str, list] = {}
    for desc in all_descriptions:
        about = desc.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about", "")
        by_about.setdefault(about, []).append(desc)

    merged = []
    for about, descs in by_about.items():
        primary = descs[0]
        for extra in descs[1:]:
            for child in list(extra):
                tag = child.tag
                # nur \u00fcbernehmen, wenn primary dieses Element noch nicht hat
                if primary.find(tag) is None:
                    primary.append(child)
            parent = extra.getparent()
            if parent is not None:
                parent.remove(extra)
        merged.append(primary)

    return merged

def _debug_print(*_args, **_kwargs) -> None:
    """Debug output was printed to the user's console; it is dropped (Phase 5)."""


@corrector("missing-metadata-stream-dc-title")
def correct_missing_metadata_stream_dc_title(detected_violation: DetectedViolation, pdf: Pdf):
    """
    Fix PDF/UA-1 rule 7.1-9 by ensuring the XMP metadata contains a valid dc:title.
    Preserve the existing stream object instead of replacing the whole metadata stream.

    Wichtig, damit's zuverlässig funktioniert:
    - dc:title wird aus ALLEN rdf:Description-Bl\u00f6cken entfernt (nicht nur dem ersten),
      manche PDFs (z.B. Adobe-erzeugte) haben mehrere Description-Bl\u00f6cke im selben XMP-Paket.
    - Der xpacket-Wrapper (<?xpacket begin=...?> ... <?xpacket end=...?>) wird beim
      Serialisieren manuell wieder angeh\u00e4ngt, weil etree.tostring(root, ...) nur den
      Teilbaum ab root serialisiert und die urspr\u00fcnglichen xpacket-PIs (Geschwister
      von root, nicht Kinder) sonst stillschweigend verloren gehen.
    - KEINE manuelle /Length-Zuweisung auf dem Stream-Objekt; pikepdf berechnet das
      beim metadata.write(...) selbst, ein manuelles Setzen kann eine Exception werfen.
    """
    title = _choose_title(pdf)
    if _DEBUG:
        _debug_print(f"FINAL TITLE: {repr(title)}")

    try:
        metadata = getattr(pdf.Root, "Metadata", None)

        if metadata is None:
            _create_new_xmp_stream(pdf, title)
            return

        xmp_data = metadata.read_bytes()
        root = etree.fromstring(xmp_data)
        if _DEBUG:
            _debug_print("get xmp_data")

        ns = {
            "dc": "http://purl.org/dc/elements/1.1/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "pdf": "http://ns.adobe.com/pdf/1.3/",
            "xmp": "http://ns.adobe.com/xap/1.0/",
            "xml": "http://www.w3.org/XML/1998/namespace",
        }

        all_descriptions = _merge_duplicate_descriptions(root, ns)

        if _DEBUG:
            _debug_print(f"Anzahl Description-Bl\u00f6cke (vorher): {len(all_descriptions)}")
            for i, d in enumerate(all_descriptions):
                children = [etree.QName(c).localname for c in d]
                _debug_print(f"  Block {i}: {children}")

        if not all_descriptions:
            rdf_rdf = root.find(".//rdf:RDF", ns)
            if rdf_rdf is None:
                rdf_rdf = root.find(
                    ".//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF"
                )
            if rdf_rdf is None:
                _create_new_xmp_stream(pdf, title)
                return
            rdf_desc = etree.Element(
                "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description",
                attrib={"{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about": ""},
            )
            rdf_rdf.append(rdf_desc)
            all_descriptions = [rdf_desc]

        # dc:title aus ALLEN Description-Bl\u00f6cken entfernen, nicht nur dem ersten
        for desc in all_descriptions:
            for existing_title in list(desc.findall("./dc:title", ns)):
                desc.remove(existing_title)
            for existing_title in list(
                desc.findall(".//{http://purl.org/dc/elements/1.1/}title")
            ):
                desc.remove(existing_title)

        # neues dc:title in EINEN Block einf\u00fcgen (den ersten reicht)
        target_desc = all_descriptions[0]
        dc_title = etree.Element("{http://purl.org/dc/elements/1.1/}title")
        rdf_alt = etree.Element("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Alt")
        rdf_li = etree.Element("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}li")
        rdf_li.set("{http://www.w3.org/XML/1998/namespace}lang", "x-default")
        rdf_li.text = title
        rdf_alt.append(rdf_li)
        dc_title.append(rdf_alt)
        target_desc.append(dc_title)

        if _DEBUG:
            all_descriptions_after = root.findall(".//rdf:Description", ns)
            _debug_print(f"Anzahl Description-Bl\u00f6cke (nachher): {len(all_descriptions_after)}")
            for i, d in enumerate(all_descriptions_after):
                title_el = d.find("./dc:title", ns)
                _debug_print(f"  Block {i}: dc:title vorhanden = {title_el is not None}")

        # xpacket-Wrapper manuell erhalten statt etree.tostring(root, xml_declaration=True),
        # das nur den Teilbaum ab root serialisiert und dabei die urspr\u00fcnglichen
        # xpacket-Processing-Instructions (Geschwister von root) verwirft.
        body = etree.tostring(root, encoding="unicode")
        new_xmp_data = (
            '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
            + body
            + '\n<?xpacket end="w"?>'
        ).encode("utf-8")

        if _DEBUG:
            _debug_print("--- NEW XMP HEAD ---")
            _debug_print(new_xmp_data[:250])
            _debug_print("--- NEW XMP TAIL ---")
            _debug_print(new_xmp_data[-250:])

        # IMPORTANT: write back to the SAME metadata stream object
        # Do NOT replace the stream object via pdf.Root.Metadata = ...
        try:
            metadata.write(new_xmp_data)
        except Exception:
            # Fallback: direct data manipulation if write() fails
            metadata._data = new_xmp_data

        # KEINE manuelle Length-Zuweisung - pikepdf berechnet das selbst bei write().
        # if hasattr(metadata, "Length"):
        #     metadata.Length = len(new_xmp_data)

        if _DEBUG:
            _debug_print(f"Updated existing XMP stream with dc:title: {title}")

    except Exception as e:
        # Never replace an existing metadata packet: it can hold the PDF/A and PDF/UA
        # identification and other properties that would be lost.
        raise CouldNotCorrectDetectedViolationException(
            f"missing-metadata-stream-dc-title: the existing XMP metadata could not be updated: {e}"
        ) from e


def _existing_info_title(pdf: Pdf) -> str | None:
    if pdf.docinfo is None:
        return None
    title = pdf.docinfo.get("/Title")
    return str(title).strip() or None if title else None


_JUNK_TITLE = re.compile(
    r"^(microsoft (word|powerpoint|excel)\s*-|untitled|unbenannt|document\d*$|dokument\d*$)"
    r"|\.(docx?|pptx?|xlsx?|odt|tex|pdf|indd)$",
    re.IGNORECASE,
)


def _usable_existing_title(title: str | None) -> str | None:
    """The document-info title, unless it is a file name or an authoring-tool default."""
    if not title or _JUNK_TITLE.search(title.strip()):
        return None
    return title.strip()


def _title_from_layout(pdf: Pdf) -> str | None:
    """
    The title as a reader sees it: the lines in the largest font size in the upper half of
    page 1 (at least 3 letters, at most 3 lines). Works without an AI.
    """
    import io
    import fitz

    if len(pdf.pages) == 0:
        return None
    buffer = io.BytesIO()
    single = Pdf.new()
    single.pages.append(pdf.pages[0])
    single.save(buffer)
    try:
        with fitz.open(stream=buffer.getvalue(), filetype="pdf") as document:
            page = document[0]
            lines = []
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    text = "".join(span["text"] for span in line["spans"]).strip()
                    size = max((span["size"] for span in line["spans"]), default=0)
                    if line["bbox"][1] < page.rect.height / 2 and sum(c.isalpha() for c in text) >= 3:
                        lines.append((round(size, 1), line["bbox"][1], text))
    except Exception:
        return None
    if not lines:
        return None
    largest = max(size for size, _, _ in lines)
    title_lines = [text for size, _, text in sorted(lines, key=lambda item: item[1]) if size == largest][:3]
    title = " ".join(title_lines)
    visible = [char for char in title if not char.isspace()]
    if len(title) < 3 or sum(char.isalpha() for char in visible) < 0.6 * len(visible):
        return None                                    # mostly symbols: probably a scan, not a title
    return title[:200]


def _title_from_file_name(pdf: Pdf) -> str | None:
    name = Path(str(getattr(pdf, "filename", "") or "")).stem
    name = re.sub(r"[_\-]+", " ", name).strip()
    return name or None


def _choose_title(pdf: Pdf) -> str:
    """
    Pick the title: existing document-info title, else the largest text on page 1 (what readers
    see as the title; exact, so it comes before the AI), else a title the AI writes from page 1,
    else the file name. Taken, generated and file-name titles are reported for review.
    """
    existing = _usable_existing_title(_existing_info_title(pdf))
    if existing:
        return _sanitize_for_xmp(existing)

    from pdfaccessguru.LLM.fallback import ai_available, note_fallback
    from_layout = _sanitize_for_xmp(_title_from_layout(pdf) or "")
    if from_layout:
        if not ai_available():
            note_fallback("title")
        report_review(f"The document title was taken from the largest text on page 1: '{from_layout}'. Please check it.")
        return from_layout

    generated = _llm_title_from_first_page(pdf)
    if generated:
        report_review(f"Document title was generated by a language model from page 1: '{generated}'. Please check it.")
        return generated

    from_file = _sanitize_for_xmp(_title_from_file_name(pdf) or "")
    if from_file:
        report_review(f"No document title was found; the file name was used as title: '{from_file}'. Please enter the real title.")
        return from_file

    report_review(f"No document title could be determined; '{FALLBACK_TITLE}' was written. Please enter the real title.")
    return FALLBACK_TITLE


def _llm_title_from_first_page(pdf: Pdf) -> str | None:
    """A title generated from page 1, or None if no usable title could be generated."""
    if len(pdf.pages) == 0:
        return None

    try:
        text = extract_text_from_page(pdf.pages[0])
    except Exception:
        return None

    if not text:
        return None

    system_prompt = (
        "You generate a short, meaningful document title based on the "
        "provided excerpt of the document's content. The title must clearly "
        "identify the document and accurately reflect its content. Respond "
        "with the title only, no quotes, no explanation."
    )
    user_prompt = f"Document excerpt:\n{text[:MAX_TITLE_SOURCE_LENGTH]}"

    try:
        response = OpenRouterBaseProvider().send_message(system_prompt, user_prompt)
    except Exception:
        return None

    if is_unusable_llm_text(response):
        return None
    title = _sanitize_for_xmp(clean_llm_text(response))
    return title[:200] or None


def _create_new_xmp_stream(pdf: Pdf, title: str):
    """
    Create a completely new XMP stream with the required dc:title structure.
    This is used as a fallback when no existing metadata stream exists.
    """
    if _DEBUG:
        _debug_print(f"Creating new XMP stream with title: {title}")

    xmp_template = '''<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="PDFAccessGuru">
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about=""
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:pdf="http://ns.adobe.com/pdf/1.3/"
            xmlns:xmp="http://ns.adobe.com/xap/1.0/">
            <dc:title>
                <rdf:Alt>
                    <rdf:li xml:lang="x-default">{title}</rdf:li>
                </rdf:Alt>
            </dc:title>
        </rdf:Description>
    </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>'''

    xmp_data = xmp_template.format(title=escape(title)).encode("utf-8")
    pdf.Root.Metadata = pdf.make_stream(xmp_data)
    pdf.Root.Metadata.Type = pikepdf.Name("/Metadata")
    pdf.Root.Metadata.Subtype = pikepdf.Name("/XML")
    if _DEBUG:
        _debug_print(f"Created new XMP stream with title: {title}")