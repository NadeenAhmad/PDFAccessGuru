import mimetypes

from .common import CouldNotCorrectDetectedViolationException, DetectedViolation, Pdf, corrector, pikepdf

VIOLATION_NAME = "ct-missing-media-clip-data"


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


def infer_content_type_from_bytes(media_bytes: bytes) -> str | None:
    if media_bytes.startswith(b"\x1aE\xdf\xa3"):
        return "video/webm"
    if media_bytes[4:8] == b"ftyp":
        return "video/mp4"
    if media_bytes.startswith(b"RIFF") and media_bytes[8:12] == b"AVI ":
        return "video/x-msvideo"
    if media_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if media_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if media_bytes.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"

    return None


def infer_content_type_from_file_spec(media_clip_data: pikepdf.Dictionary) -> str | None:
    try:
        file_spec = media_clip_data["/D"]
    except (KeyError, TypeError):
        return None

    if not hasattr(file_spec, "get"):
        return None

    filename = file_spec.get("/UF") or file_spec.get("/F")
    if filename is None:
        return None

    guessed_type, _ = mimetypes.guess_type(str(filename))
    return guessed_type


def infer_media_clip_content_type(media_clip_data: pikepdf.Dictionary) -> str:
    media_bytes = extract_media_clip_data_bytes(media_clip_data)
    if media_bytes is not None:
        content_type = infer_content_type_from_bytes(media_bytes)
        if content_type is not None:
            return content_type

    content_type = infer_content_type_from_file_spec(media_clip_data)
    if content_type is not None:
        return content_type

    return ""


@corrector(VIOLATION_NAME)
def correct_ct_missing_media_clip_data(detected_violation: DetectedViolation, pdf: Pdf):
    """
    VeraPdf rule_id: 7.18.6.2-1

    Violation description:
    The media clip data dictionary is missing the /CT key.

    Correction strategy:
    The affected element is the media clip data dictionary at /A -> /R -> /C.
    Infer the media content type from the embedded file bytes or file
    specification and add it as the missing /CT entry. If the type cannot be
    inferred, write an empty string because veraPDF only requires /CT to exist.
    """
    affected_element = detected_violation.affected_element

    if not isinstance(affected_element, pikepdf.Dictionary):
        raise CouldNotCorrectDetectedViolationException(VIOLATION_NAME)

    affected_element["/CT"] = pikepdf.String(infer_media_clip_content_type(affected_element))
