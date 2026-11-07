import re
import io
import hashlib
import json
import logging
import time
from dataclasses import dataclass

import pdfplumber
from pdfplumber.page import Page
from pdfplumber.pdf import PDF as PdfPlumberDocument
from pikepdf import Array, Dictionary, Name, Pdf, String
from requests.exceptions import RequestException

from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
from pdfaccessguru.exceptions.corrector_exceptions.could_not_correct_detected_violation_exception import (
    CouldNotCorrectDetectedViolationException,
)
from pdfaccessguru.model.LLM.image import Image
from pdfaccessguru.model.detected_violation import DetectedViolation
from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.corrector import corrector
from pdfaccessguru.pipeline.reporting.writer import report_review


_MAX_ALT_TEXT_LENGTH = 1000
_MAX_CONTEXT_LENGTH = 50000
_RENDER_RESOLUTION = 288
_MAX_RENDER_DIMENSION = 2048
_CROP_PADDING_POINTS = 2.0
_PDF_CACHE_ATTRIBUTE = "_pdf_access_guru_7_3_1_cache"

_LOGGER = logging.getLogger(__name__)


@dataclass
class _FigureCorrectionCache:
    """Reusable PDF data for all 7.3-1 violations in one pipeline run."""

    snapshot: io.BytesIO
    extracted_pdf: PdfPlumberDocument
    page_text_by_index: dict[int, str | None]
    alt_text_by_request: dict[str, str]

    def __del__(self) -> None:
        """Release the cached pdfplumber document when its pikepdf owner is gone."""
        try:
            self.extracted_pdf.close()
        except Exception:
            pass
        try:
            self.snapshot.close()
        except Exception:
            pass


@dataclass(frozen=True)
class _RenderedFigure:
    """The rendered Figure image and contextual page information for the LLM."""

    image: Image
    page_index: int
    crop_bbox: tuple[float, float, float, float]
    page_text: str | None


@corrector("figure-structure-alternate-description-missing")
def correct_figure_structure_alternate_description_missing(
    detected_violation: DetectedViolation,
    pdf: Pdf,
) -> None:
    """
    Correct veraPDF rule 7.3-1.

    The affected /Figure has neither /Alt nor /ActualText. Its visible page area
    and structure context are sent to a vision-capable LLM. A validated,
    meaningful description is then written to the Figure's /Alt entry.
    """
    figure = detected_violation.affected_element
    role_map = _get_role_map(pdf)
    if (
        not isinstance(figure, Dictionary)
        or _resolve_role(figure.get("/S"), role_map) != Name("/Figure")
    ):
        raise _correction_error(detected_violation, "affected element is not a /Figure")

    # Do not overwrite a description or replacement text supplied by the author.
    if _has_meaningful_text(figure.get("/Alt")) or _has_meaningful_text(
        figure.get("/ActualText")
    ):
        return

    correction_started = time.perf_counter()
    rendered_figure = _render_figure(pdf, figure, detected_violation)
    render_finished = time.perf_counter()
    context_json = _render_figure_context(pdf, figure, rendered_figure, role_map)
    if len(context_json) > _MAX_CONTEXT_LENGTH:
        raise _correction_error(
            detected_violation, "Figure context is too large for the LLM"
        )

    cache = _get_figure_correction_cache(pdf)
    request_key = _alt_text_request_key(context_json, rendered_figure.image)
    validated_alt_text = cache.alt_text_by_request.get(request_key)
    cache_hit = validated_alt_text is not None
    written_by_ai = True
    if validated_alt_text is None:
        validated_alt_text = _alt_text_from_ai(context_json, rendered_figure, detected_violation)
        if validated_alt_text is not None:
            cache.alt_text_by_request[request_key] = validated_alt_text
    if validated_alt_text is None:
        # No AI (or it failed): caption, text in the picture, OCR, else "Picture" (Phase 4)
        from pdfaccessguru.LLM.fallback import ai_available, note_fallback
        from pdfaccessguru.pipeline.PDFAccessGuruCorrect.correctors.descriptions.pictures import describe_picture

        validated_alt_text, source = describe_picture(
            pdf, figure, rendered_figure.image.image_data, rendered_figure.page_text)
        written_by_ai = False
        if not ai_available():
            note_fallback("alt_text")

    # Write only after image extraction and text generation succeeded.
    figure["/Alt"] = String(validated_alt_text)
    how = "by an AI model" if written_by_ai else "from the text around the picture (no AI)"
    report_review(
        f"This picture description was written {how}: '{validated_alt_text}'. Please check it.",
        context=_caption_or_nearby_text(rendered_figure.page_text),
        image_png=rendered_figure.image.image_data,
        page=rendered_figure.page_index + 1,
    )
    _LOGGER.debug(
        "7.3-1 corrected Figure: render=%.3fs, alt_text=%.3fs, cache_hit=%s",
        render_finished - correction_started,
        time.perf_counter() - render_finished,
        cache_hit,
    )


def _alt_text_from_ai(context_json: str, rendered_figure, detected_violation) -> str | None:
    """The AI's description, or None if no AI is set up or its answer is not usable."""
    from pdfaccessguru.LLM.fallback import ai_available
    from pdfaccessguru.exceptions.llm_exceptions.open_router_connection_failed_exception import (
        OpenRouterConnectionFailedException,
    )
    if not ai_available():
        return None
    try:
        alt_text = generate_figure_alt_text(context_json, rendered_figure.image)
        return _validate_alt_text(alt_text, detected_violation)
    except (OpenRouterConnectionFailedException, CouldNotCorrectDetectedViolationException):
        return None


def generate_figure_alt_text(context_json: str, figure_image: Image) -> str:
    """Ask a vision-capable LLM for a concise, meaningful alternative text."""
    provider = OpenRouterBaseProvider()
    system_prompt, user_prompt = build_prompt_generate_figure_alt_text(context_json)
    try:
        response = provider.send_message_with_image(
            system_prompt,
            user_prompt,
            figure_image,
            json_mode=True,
        )
    except (KeyError, IndexError, TypeError, RequestException) as exception:
        raise CouldNotCorrectDetectedViolationException(
            "figure-structure-alternate-description-missing: "
            "invalid OpenRouter response"
        ) from exception

    try:
        parsed = json.loads(response)
        alt_text = parsed["alt_text"]
    except (json.JSONDecodeError, KeyError, TypeError) as exception:
        raise CouldNotCorrectDetectedViolationException(
            "figure-structure-alternate-description-missing: invalid LLM response"
        ) from exception
    if not isinstance(alt_text, str):
        raise CouldNotCorrectDetectedViolationException(
            "figure-structure-alternate-description-missing: alt text is not a string"
        )
    return alt_text


def build_prompt_generate_figure_alt_text(context_json: str) -> tuple[str, str]:
    """Build the vision prompt while keeping PDF-derived data in the user role."""
    system_prompt = """You create accessible alternative text for a PDF/UA Figure.
Describe the visible Figure accurately and concisely in the language indicated by the
PDF context. State the information or function conveyed by the Figure, not its styling.
For a logo, identify it as a logo and include readable organization text. For a chart,
state its subject, axes, trend, and important values. For an icon, state its function.
Do not start with phrases such as 'image of' or 'picture of'. Do not repeat the caption.
Keep it short: at most 125 characters where possible. Do not guess details that are not
visible. The supplied image is the rendered Figure crop; the JSON provides its
structure element and surrounding page context.

Return only JSON in this exact form:
{"alt_text": "Concise meaningful description"}"""
    user_prompt = f"Figure structure and page context:\n{context_json}"
    return system_prompt, user_prompt


def _render_figure(
    pdf: Pdf,
    figure: Dictionary,
    detected_violation: DetectedViolation,
) -> _RenderedFigure:
    """Render the Figure's page area to PNG, preferring /BBox and MCID bounds."""
    page_index = _find_page_index(pdf, figure, detected_violation)
    try:
        cache = _get_figure_correction_cache(pdf)
        page = cache.extracted_pdf.pages[page_index]
        crop_bbox = _figure_crop_bbox(figure, page)
        cropped_page = page.crop(crop_bbox)
        page_image = cropped_page.to_image(
            resolution=_safe_render_resolution(crop_bbox),
            antialias=True,
        ).original
        png = io.BytesIO()
        page_image.save(png, format="PNG")
        if page_index not in cache.page_text_by_index:
            page_text = _clean_text(page.extract_text() or "")
            cache.page_text_by_index[page_index] = page_text or None
        page_text = cache.page_text_by_index[page_index]
    except Exception as exception:
        raise _correction_error(
            detected_violation, "could not render the Figure"
        ) from exception

    return _RenderedFigure(
        image=Image(png.getvalue()),
        page_index=page_index,
        crop_bbox=crop_bbox,
        page_text=page_text or None,
    )


def _get_figure_correction_cache(pdf: Pdf) -> _FigureCorrectionCache:
    """Create the expensive PDF snapshot and pdfplumber document only once."""
    existing_cache = getattr(pdf, _PDF_CACHE_ATTRIBUTE, None)
    if isinstance(existing_cache, _FigureCorrectionCache):
        return existing_cache

    snapshot = io.BytesIO()
    try:
        pdf.save(snapshot)
        snapshot.seek(0)
        extracted_pdf = pdfplumber.open(snapshot)
    except Exception:
        snapshot.close()
        raise

    cache = _FigureCorrectionCache(
        snapshot=snapshot,
        extracted_pdf=extracted_pdf,
        page_text_by_index={},
        alt_text_by_request={},
    )
    setattr(pdf, _PDF_CACHE_ATTRIBUTE, cache)
    return cache


def _alt_text_request_key(context_json: str, image: Image) -> str:
    """Identify only byte-for-byte equivalent image-and-context requests."""
    digest = hashlib.sha256()
    digest.update(context_json.encode("utf-8"))
    digest.update(b"\0")
    digest.update(image.image_data)
    return digest.hexdigest()


def _figure_crop_bbox(
    figure: Dictionary,
    page: Page,
) -> tuple[float, float, float, float]:
    """Choose a clamped pdfplumber crop from /BBox, MCID objects or the full page."""
    pdf_bbox = _read_figure_bbox(figure)
    if pdf_bbox is not None:
        x0, y0, x1, y1 = pdf_bbox
        bbox = (x0, float(page.height) - y1, x1, float(page.height) - y0)
    else:
        bbox = _mcid_bbox(page, set(_direct_mcids(figure)))
        if bbox is None:
            bbox = (0.0, 0.0, float(page.width), float(page.height))
    return _pad_and_clamp_bbox(bbox, float(page.width), float(page.height))


def _safe_render_resolution(
    crop_bbox: tuple[float, float, float, float],
) -> int:
    """Limit raster dimensions while retaining high resolution for small Figures."""
    width = crop_bbox[2] - crop_bbox[0]
    height = crop_bbox[3] - crop_bbox[1]
    largest_dimension = max(width, height, 1.0)
    maximum_resolution = int(72 * _MAX_RENDER_DIMENSION / largest_dimension)
    # Without an AI the picture is only used for text recognition and the review list, which
    # need less detail; rendering at half resolution is about four times faster (Phase 5).
    from pdfaccessguru.LLM.fallback import ai_available
    wanted = _RENDER_RESOLUTION if ai_available() else _RENDER_RESOLUTION // 2
    return max(1, min(wanted, maximum_resolution))


def _read_figure_bbox(
    figure: Dictionary,
) -> tuple[float, float, float, float] | None:
    """Read the first valid four-number /BBox from the Figure attributes."""
    attributes = figure.get("/A")
    attribute_values = list(attributes) if isinstance(attributes, Array) else [attributes]
    for attribute in attribute_values:
        if not isinstance(attribute, Dictionary):
            continue
        bbox = attribute.get("/BBox")
        if not isinstance(bbox, Array) or len(bbox) != 4:
            continue
        try:
            values = tuple(float(str(value)) for value in bbox)
        except (TypeError, ValueError, OverflowError):
            continue
        x0, y0, x1, y1 = values
        if x1 > x0 and y1 > y0:
            return (x0, y0, x1, y1)
    return None


def _mcid_bbox(
    page: Page,
    mcids: set[int],
) -> tuple[float, float, float, float] | None:
    """Calculate the union of visible page objects owned by the Figure's MCIDs."""
    if not mcids:
        return None
    matching_objects: list[dict] = []
    for objects in page.objects.values():
        matching_objects.extend(
            obj for obj in objects if obj.get("mcid") in mcids
        )
    if not matching_objects:
        return None
    try:
        return (
            min(float(obj["x0"]) for obj in matching_objects),
            min(float(obj["top"]) for obj in matching_objects),
            max(float(obj["x1"]) for obj in matching_objects),
            max(float(obj["bottom"]) for obj in matching_objects),
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def _pad_and_clamp_bbox(
    bbox: tuple[float, float, float, float],
    page_width: float,
    page_height: float,
) -> tuple[float, float, float, float]:
    """Add small visual padding and keep the crop inside the page boundaries."""
    x0, top, x1, bottom = bbox
    padded = (
        max(0.0, x0 - _CROP_PADDING_POINTS),
        max(0.0, top - _CROP_PADDING_POINTS),
        min(page_width, x1 + _CROP_PADDING_POINTS),
        min(page_height, bottom + _CROP_PADDING_POINTS),
    )
    if padded[2] <= padded[0] or padded[3] <= padded[1]:
        return (0.0, 0.0, page_width, page_height)
    return padded


def _find_page_index(
    pdf: Pdf,
    figure: Dictionary,
    detected_violation: DetectedViolation,
) -> int:
    """Resolve the Figure's explicit or inherited /Pg reference to a page index."""
    current: Dictionary | None = figure
    page = _direct_page_reference(figure)
    visited: set[tuple[int, int] | int] = set()
    while page is None and current is not None:
        identity = _element_identity(current)
        if identity in visited:
            break
        visited.add(identity)
        candidate_page = current.get("/Pg")
        if isinstance(candidate_page, Dictionary):
            page = candidate_page
            break
        parent = current.get("/P")
        current = parent if isinstance(parent, Dictionary) else None

    if page is None:
        raise _correction_error(detected_violation, "Figure has no page reference")
    page_objgen = _objgen_tuple(page)
    for page_index, pdf_page in enumerate(pdf.pages):
        if _objgen_tuple(pdf_page) == page_objgen:
            return page_index
    raise _correction_error(detected_violation, "Figure page is not part of the PDF")


def _direct_page_reference(element: Dictionary) -> Dictionary | None:
    """Read /Pg from the Figure itself or one of its direct MCR dictionaries."""
    page = element.get("/Pg")
    if isinstance(page, Dictionary):
        return page
    children = element.get("/K")
    values = list(children) if isinstance(children, Array) else [children]
    for value in values:
        if isinstance(value, Dictionary):
            child_page = value.get("/Pg")
            if isinstance(child_page, Dictionary):
                return child_page
    return None


def _render_figure_context(
    pdf: Pdf,
    figure: Dictionary,
    rendered_figure: _RenderedFigure,
    role_map: Dictionary | None,
) -> str:
    """Serialize the Figure structure element and nearby document information."""
    parent = figure.get("/P")
    parent_dict = parent if isinstance(parent, Dictionary) else None
    language = _inherited_text_value(figure, "/Lang")
    document_root = pdf.Root
    if language is None and isinstance(document_root, Dictionary):
        language = _inherited_text_value(document_root, "/Lang")
    serializable = {
        "figure": {
            "tag": str(_resolve_role(figure.get("/S"), role_map)),
            "title": _text_value(figure.get("/T")),
            "expanded_text": _text_value(figure.get("/E")),
            "direct_mcids": _direct_mcids(figure),
            "child_tags": [
                str(_resolve_role(child.get("/S"), role_map))
                for child in _structure_children(figure)
            ],
        },
        "parent": {
            "tag": str(_resolve_role(parent_dict.get("/S"), role_map))
            if parent_dict is not None
            else None,
            "title": _text_value(parent_dict.get("/T"))
            if parent_dict is not None
            else None,
        },
        "document_language": language,
        "page_number": rendered_figure.page_index + 1,
        "crop_bbox": rendered_figure.crop_bbox,
        "page_text_context": rendered_figure.page_text,
    }
    return json.dumps(serializable, ensure_ascii=False, separators=(",", ":"))


_CAPTION_START = re.compile(r"^\s*(fig(ure)?\.?|abb(ildung)?\.?|image|bild|chart|diagram)\s*\d", re.IGNORECASE)


def _caption_or_nearby_text(page_text: object, max_length: int = 300) -> str | None:
    """A figure caption from the page text if one is found, otherwise the start of the nearby text."""
    if not isinstance(page_text, str) or not page_text.strip():
        return None
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    for line in lines:
        if _CAPTION_START.match(line):
            return "Caption: " + line[:max_length]
    return "Nearby text: " + " ".join(lines)[:max_length]


def _validate_alt_text(
    alt_text: str,
    detected_violation: DetectedViolation,
) -> str:
    """Normalize the LLM description and reject empty, generic or excessive text."""
    normalized = _clean_text(alt_text)
    if not normalized:
        raise _correction_error(detected_violation, "LLM returned empty alt text")
    if len(normalized) > _MAX_ALT_TEXT_LENGTH:
        raise _correction_error(detected_violation, "LLM alt text is too long")
    if normalized.casefold() in {
        "image",
        "figure",
        "graphic",
        "image of",
        "figure image",
        "no description available",
    }:
        raise _correction_error(detected_violation, "LLM returned generic alt text")
    return normalized


def _direct_mcids(element: Dictionary) -> list[int]:
    """Collect MCIDs owned by the Figure without entering child StructElems."""
    mcids: list[int] = []

    def collect(value: object) -> None:
        if isinstance(value, int):
            mcids.append(value)
        elif isinstance(value, Array):
            for item in value:
                collect(item)
        elif isinstance(value, Dictionary):
            if value.get("/S") is not None:
                return
            mcid = value.get("/MCID")
            if mcid is not None:
                try:
                    mcids.append(int(str(mcid)))
                except (TypeError, ValueError, OverflowError):
                    return

    collect(element.get("/K"))
    return mcids


def _structure_children(element: Dictionary) -> list[Dictionary]:
    """Return only child structure elements from the Figure's /K value."""
    children = element.get("/K")
    values = list(children) if isinstance(children, Array) else [children]
    return [
        value
        for value in values
        if isinstance(value, Dictionary) and value.get("/S") is not None
    ]


def _get_role_map(pdf: Pdf) -> Dictionary | None:
    """Return the document RoleMap used by custom Figure structure types."""
    structure_tree_root = pdf.Root.get("/StructTreeRoot")
    if not isinstance(structure_tree_root, Dictionary):
        return None
    role_map = structure_tree_root.get("/RoleMap")
    return role_map if isinstance(role_map, Dictionary) else None


def _resolve_role(role: object, role_map: Dictionary | None) -> object:
    """Resolve custom structure roles while protecting against RoleMap cycles."""
    if role_map is None:
        return role
    current = role
    visited: set[str] = set()
    while isinstance(current, Name):
        role_name = str(current)
        if role_name in visited or role_name not in role_map:
            break
        visited.add(role_name)
        mapped_role = role_map.get(role_name)
        if not isinstance(mapped_role, Name):
            break
        current = mapped_role
    return current


def _inherited_text_value(element: Dictionary, key: str) -> str | None:
    """Read a text value from an element or its structure ancestors."""
    current: Dictionary | None = element
    visited: set[tuple[int, int] | int] = set()
    while current is not None:
        identity = _element_identity(current)
        if identity in visited:
            break
        visited.add(identity)
        value = _text_value(current.get(key))
        if value:
            return value
        parent = current.get("/P")
        current = parent if isinstance(parent, Dictionary) else None
    return None


def _text_value(value: object) -> str | None:
    """Normalize an optional PDF string-like value."""
    if value is None:
        return None
    text = _clean_text(str(value))
    return text or None


def _has_meaningful_text(value: object) -> bool:
    """Check whether an existing /Alt or /ActualText contains non-whitespace text."""
    return _text_value(value) is not None


def _clean_text(text: str) -> str:
    """Collapse whitespace and remove embedded null characters."""
    return " ".join(text.replace("\x00", "").split())


def _element_identity(element: Dictionary) -> tuple[int, int] | int:
    """Return a stable identity for direct and indirect pikepdf dictionaries."""
    objgen = _objgen_tuple(element)
    return objgen if objgen != (0, 0) else id(element)


def _objgen_tuple(element: object) -> tuple[int, int]:
    """Normalize pikepdf's broadly typed objgen property to an integer tuple."""
    objgen = getattr(element, "objgen", None)
    if (
        isinstance(objgen, tuple)
        and len(objgen) == 2
        and isinstance(objgen[0], int)
        and isinstance(objgen[1], int)
    ):
        return (objgen[0], objgen[1])
    return (0, 0)


def _correction_error(
    detected_violation: DetectedViolation,
    reason: str,
) -> CouldNotCorrectDetectedViolationException:
    """Create a correction exception containing the violation name and reason."""
    return CouldNotCorrectDetectedViolationException(
        f"{detected_violation.violation.name}: {reason}"
    )
