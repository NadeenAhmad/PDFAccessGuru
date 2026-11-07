"""PDF names as text, also when they are not UTF-8 (e.g. Japanese font names in Shift-JIS)."""

from __future__ import annotations

import re


def name_text(value) -> str:
    """str() of a pikepdf name or string; bytes that are not UTF-8 are kept one character per byte
    instead of failing (str() raises UnicodeDecodeError for names like b'/ARP\\x83S\\x83V...')."""
    try:
        return str(value)
    except UnicodeDecodeError:
        try:
            raw = value.unparse()
        except Exception:
            return repr(value)
        text = raw.decode("latin-1")
        return re.sub(r"#([0-9A-Fa-f]{2})", lambda m: chr(int(m.group(1), 16)), text)


def same_font_name(ours: str | None, reported: str | None) -> bool:
    """veraPDF prints names that are not UTF-8 with replacement characters ("ARP\\ufffdS..."); then the
    readable start of the name must match (at least 6 characters)."""
    if ours is None or reported is None:
        return False
    if ours == reported:
        return True
    readable = re.split(r"[^\x20-\x7e]", reported)[0]
    return readable != reported and len(readable) >= 6 and ours.startswith(readable)
