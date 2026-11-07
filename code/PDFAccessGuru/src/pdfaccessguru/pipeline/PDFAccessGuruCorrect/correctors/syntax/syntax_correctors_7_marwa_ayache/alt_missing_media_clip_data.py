import tempfile
from io import BytesIO
from pathlib import Path

from .common import CouldNotCorrectDetectedViolationException, DetectedViolation, Pdf, corrector, pikepdf
from pdfaccessguru.model.supplementary_information.supplementary_information import LanguageContextSupplementaryInformation
from pdfaccessguru.LLM.output_checks import is_unusable_llm_text
from pdfaccessguru.pipeline.reporting.writer import report_review

VIOLATION_NAME = "alt-missing-media-clip-data"
MAX_ALT_LENGTH = 240
DEFAULT_ALT_LANGUAGE = "en-US"
FALLBACK_ALT_TEXT = "Embedded media content."


def get_media_clip_content_type(media_clip_data: pikepdf.Dictionary) -> str:
    content_type = media_clip_data.get("/CT", "")
    return str(content_type).lower().split(";", maxsplit=1)[0].strip()


def extract_media_clip_data_bytes(media_clip_data: pikepdf.Dictionary) -> bytes | None:
    """
    Return the bytes from a media clip's embedded file stream, if present.

    Expected PDF path:
    /MediaClip -> /D -> /EF -> /F
    """
    try:
        file_spec = media_clip_data["/D"]
        embedded_files = file_spec["/EF"]
        embedded_file_stream = embedded_files["/F"]
    except (KeyError, TypeError):
        return None

    if not hasattr(embedded_file_stream, "read_bytes"):
        return None

    return embedded_file_stream.read_bytes()


def extract_representative_video_frame_png(media_bytes: bytes, content_type: str) -> bytes | None:
    """
    Extract one representative video frame as PNG bytes.

    OpenCV needs a file path for VideoCapture, so the embedded media bytes are
    written to a temporary file and deleted again after the frame is extracted.
    """
    try:
        import cv2
    except ImportError as error:
        raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME) from error

    video_suffix = _video_suffix_from_media_bytes(media_bytes) or _video_suffix_from_content_type(content_type)
    video_path = None
    frame_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=video_suffix, delete=False) as video_file:
            video_file.write(media_bytes)
            video_path = Path(video_file.name)

        frame = _read_representative_frame_with_opencv(video_path, cv2)
        if frame is None:
            frame = _read_representative_frame_with_pyav(video_path)
        if frame is None:
            return None

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as frame_file:
            frame_path = Path(frame_file.name)

        if not cv2.imwrite(str(frame_path), frame):
            return None

        return frame_path.read_bytes()
    finally:
        if video_path is not None:
            video_path.unlink(missing_ok=True)
        if frame_path is not None:
            frame_path.unlink(missing_ok=True)


def _read_representative_frame_with_opencv(video_path: Path, cv2):
    capture = cv2.VideoCapture(str(video_path))
    try:
        if not capture.isOpened():
            return None

        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if frame_count > 1:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_count // 2)

        success, frame = capture.read()
        if not success:
            return None

        return frame
    finally:
        capture.release()


def _read_representative_frame_with_pyav(video_path: Path):
    """
    Decode the first available video frame with PyAV.

    This is useful for WebM streams that some OpenCV wheels cannot decode.
    The frame is returned in OpenCV's BGR ndarray format so cv2.imwrite can
    still write the PNG output.
    """
    try:
        import av
    except ImportError as error:
        raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME) from error

    container = av.open(str(video_path))
    try:
        video_stream = next((stream for stream in container.streams if stream.type == "video"), None)
        if video_stream is None:
            return None

        for frame in container.decode(video_stream):
            return frame.to_ndarray(format="bgr24") # type: ignore[attr-defined] 
    finally:
        container.close()

    return None


def image_media_bytes_to_png(media_bytes: bytes) -> bytes | None:
    """
    Return PNG bytes for an embedded image media clip.

    The OpenRouter image provider sends images as image/png data URLs. Embedded
    PNG data can be used as-is. Other image formats are converted with Pillow
    when it is available.
    """
    if media_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return media_bytes

    try:
        from PIL import Image as PILImage
    except ImportError:
        return None

    try:
        with PILImage.open(BytesIO(media_bytes)) as image:
            png_buffer = BytesIO()
            image.save(png_buffer, format="PNG")
            return png_buffer.getvalue()
    except Exception:
        return None


def prompt_media_clip_alt_text(media_clip_data: pikepdf.Dictionary, language_tag: str) -> str:
    """
    Ask the configured OpenRouter provider for the missing media clip /Alt text.

    For video media clips, a representative frame is extracted and sent to the
    vision-capable model. For image media clips, the embedded image is sent
    directly after converting it to PNG if needed. The response is sanitized
    before it is written into the PDF.
    """
    media_bytes = extract_media_clip_data_bytes(media_clip_data)
    if media_bytes is None:
        raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)

    content_type = get_media_clip_content_type(media_clip_data)
    system_prompt, user_prompt = build_prompt_media_clip_alt_text(media_clip_data, len(media_bytes), language_tag)

    if content_type.startswith("video/"):
        frame_png = extract_representative_video_frame_png(media_bytes, content_type)
        if frame_png is None:
            raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)

        from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
        from pdfaccessguru.model.LLM.image import Image

        response = OpenRouterBaseProvider().send_message_with_image(
            system_prompt,
            user_prompt,
            Image(frame_png),
        )
    elif content_type.startswith("image/"):
        image_png = image_media_bytes_to_png(media_bytes)
        if image_png is None:
            raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)

        from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider
        from pdfaccessguru.model.LLM.image import Image

        response = OpenRouterBaseProvider().send_message_with_image(
            system_prompt,
            user_prompt,
            Image(image_png),
        )
    else:
        from pdfaccessguru.LLM.providers.openrouter_provider import OpenRouterBaseProvider

        response = OpenRouterBaseProvider().send_message(system_prompt, user_prompt)

    alt_text = _sanitize_alt_response(response)
    if not alt_text:
        raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)

    return alt_text


def build_prompt_media_clip_alt_text(
    media_clip_data: pikepdf.Dictionary,
    media_size_bytes: int,
    language_tag: str,
) -> tuple[str, str]:
    """
    Build a role-play prompt pair for generating a media clip /Alt value.
    """
    prompt_dir = Path(__file__).with_name("prompts")
    system_prompt = (prompt_dir / "media_clip_alt_system_prompt.txt").read_text(encoding="utf-8")
    user_prompt_template = (prompt_dir / "media_clip_alt_user_prompt.txt").read_text(encoding="utf-8")

    user_prompt = user_prompt_template.replace(
        "{{MEDIA_CLIP_CONTEXT}}",
        _build_media_clip_context(media_clip_data, media_size_bytes),
    ).replace(
        "{{ALT_LANGUAGE_TAG}}",
        language_tag,
    )

    return system_prompt, user_prompt


def _build_media_clip_context(media_clip_data: pikepdf.Dictionary, media_size_bytes: int) -> str:
    fields = {
        "Type": media_clip_data.get("/Type"),
        "Subtype": media_clip_data.get("/S"),
        "Content-Type": media_clip_data.get("/CT"),
        "File Specification": media_clip_data.get("/D"),
        "Media Size Bytes": media_size_bytes,
    }
    lines = []

    for label, value in fields.items():
        if value is not None:
            lines.append(f"{label}: {_stringify_pdf_value(value)}")

    return "\n".join(lines) if lines else "No additional media clip context is available."


def _stringify_pdf_value(value: object) -> str:
    return str(value)


def _sanitize_alt_response(response: str) -> str:
    alt_text = response.strip().strip('"').strip("'").strip()
    alt_text = " ".join(alt_text.split())

    if not alt_text:
        return ""

    return alt_text[:MAX_ALT_LENGTH].rstrip()


def _video_suffix_from_content_type(content_type: str) -> str:
    suffix_by_content_type = {
        "video/mp4": ".mp4",
        "video/webm": ".webm",
        "video/quicktime": ".mov",
        "video/x-msvideo": ".avi",
        "video/mpeg": ".mpeg",
    }

    return suffix_by_content_type.get(content_type, ".video")


def _video_suffix_from_media_bytes(media_bytes: bytes) -> str | None:
    if media_bytes.startswith(b"\x1aE\xdf\xa3"):
        return ".webm"
    if media_bytes[4:12] in (b"ftypmp42", b"ftypisom", b"ftypMSNV", b"ftypavc1", b"ftypM4V "):
        return ".mp4"
    if media_bytes.startswith(b"RIFF") and media_bytes[8:12] == b"AVI ":
        return ".avi"

    return None


def get_alt_language(detected_violation: DetectedViolation) -> str:
    for supplementary_information in detected_violation.supplementary_information:
        if isinstance(supplementary_information, LanguageContextSupplementaryInformation):
            return supplementary_information.language_tag

    return DEFAULT_ALT_LANGUAGE


def get_fallback_alt_text() -> str:
    return FALLBACK_ALT_TEXT


@corrector("alt-missing-media-clip-data")
def correct_alt_missing_media_clip_data(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.18.6.2-2

    Violation description:
    The media clip data dictionary(at /A -> /R -> /C) is missing the /Alt key.

    Correction strategy:
    Extract the embedded media bytes, generate a concise media summary with the
    configured LLM provider, and store the generated text as /Alt.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)

    language = get_alt_language(detected_violation)
    try:
        alt_text = prompt_media_clip_alt_text(affected_element, language)
    except Exception:
        alt_text = ""
    if is_unusable_llm_text(alt_text):
        alt_text = get_fallback_alt_text()
        report_review(f"Embedded media got only a generic description ('{alt_text}') because no description could be generated. Please describe the media.")
    else:
        report_review(f"Embedded media description was generated by a language model from a single frame: '{alt_text}'. Please check it.")

    affected_element["/Alt"] = pikepdf.Array(
        [
            pikepdf.String(language),
            pikepdf.String(alt_text),
            pikepdf.String(""),
            pikepdf.String(alt_text),
        ]
    )
