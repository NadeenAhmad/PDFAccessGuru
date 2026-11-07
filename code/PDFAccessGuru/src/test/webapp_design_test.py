"""Phase 7c: the app's colours keep enough contrast in light and dark mode (WCAG AAA for text)."""

from __future__ import annotations

import re

import pytest

from pdfaccessguru.webapp.pages import CSS, LOGO

TEXT_PAIRS = [("ink", "card"), ("ink", "paper"), ("muted", "card"), ("muted", "paper"), ("navy", "card"),
              ("navy", "paper"), ("link", "card"), ("link", "paper"), ("on-teal", "teal"), ("ok-ink", "ok-bg"),
              ("warn-ink", "warn-bg"), ("error", "card"), ("ink", "ok-bg")]
UI_PAIRS = [("line", "card"), ("line", "paper"), ("focus", "card"), ("focus", "paper"), ("teal", "card"),
            ("teal", "paper"), ("logo-ink", "card"), ("logo-teal", "card")]


def _palettes() -> dict[str, dict[str, str]]:
    light = dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-f]{6})", CSS.split("@media (prefers-color-scheme: dark)")[0]))
    dark_block = CSS.split("@media (prefers-color-scheme: dark)")[1].split("}\n}")[0]
    dark = {**light, **dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-f]{6})", dark_block))}
    return {"light": light, "dark": dark}


def _luminance(color: str) -> float:
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_text_has_at_least_7_to_1_and_controls_3_to_1(mode):
    colors = _palettes()[mode]
    weak = [(f, b, round(contrast(colors[f], colors[b]), 2)) for f, b in TEXT_PAIRS if contrast(colors[f], colors[b]) < 7]
    weak += [(f, b, round(contrast(colors[f], colors[b]), 2)) for f, b in UI_PAIRS if contrast(colors[f], colors[b]) < 3]
    assert not weak, weak


def test_the_logo_is_hidden_from_screen_readers_and_follows_the_theme():
    assert 'aria-hidden="true"' in LOGO and "<title" not in LOGO
    assert 'class="ink"' in LOGO and 'class="teal"' in LOGO and "#0B2A5B" not in LOGO
