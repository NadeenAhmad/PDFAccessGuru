"""
Checks that everything PDFAccessGuru needs is installed (used by `pdfaccessguru doctor`
and by the app at start). Every result says in plain words what to do if something is missing.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from pdfaccessguru.external_tools import VERAPDF_VERSION, find_fallback_fonts, find_java, find_verapdf, verapdf_version
from pdfaccessguru.utils.environment_variables import load_environment_variables, user_env_file


@dataclass(frozen=True)
class SetupCheck:
    name: str
    ok: bool
    detail: str
    how_to_fix: str = ""
    optional: bool = False


def run_setup_checks() -> list[SetupCheck]:
    load_environment_variables()
    checks: list[SetupCheck] = []

    python_ok = sys.version_info >= (3, 12)
    checks.append(SetupCheck(
        "Python", python_ok, f"version {sys.version.split()[0]}",
        "" if python_ok else "Install PDFAccessGuru again with the installer from the website; it brings the right Python.",
    ))

    java = find_java()
    checks.append(SetupCheck(
        "Java (needed by the checker)", java is not None, str(java) if java else "not found",
        "" if java else "Run 'pdfaccessguru doctor --install' to download it (no admin rights needed).",
    ))

    verapdf = find_verapdf()
    version = verapdf_version(verapdf) if verapdf and java else None
    if verapdf is None:
        checks.append(SetupCheck(
            "veraPDF (the accessibility checker)", False, "not found",
            "Run 'pdfaccessguru doctor --install' to download it (no admin rights needed).",
        ))
    else:
        checks.append(SetupCheck(
            "veraPDF (the accessibility checker)", version is not None,
            f"version {version}" if version else f"found at {verapdf}, but it does not start",
            "" if version else "Run 'pdfaccessguru doctor --install' to download a working copy.",
        ))
        if version and version != VERAPDF_VERSION:
            checks.append(SetupCheck(
                "veraPDF version", False, f"{version} (PDFAccessGuru is tested with {VERAPDF_VERSION})",
                "Results may differ slightly. Run 'pdfaccessguru doctor --install' to get the tested version.",
                optional=True,
            ))

    fonts = find_fallback_fonts()
    checks.append(SetupCheck(
        "Fonts for embedding", fonts is not None, "installed" if fonts else "not found",
        "" if fonts else "Run 'pdfaccessguru doctor --install' to download them (2 MB). Without them, "
                         "fonts that are missing from a PDF can only be added if they are on this computer.",
        optional=True,
    ))

    from pdfaccessguru.LLM.client import settings
    ai = settings(refresh=True)
    checks.append(SetupCheck(
        "AI model (optional)", ai.available, ai.describe(),
        "" if ai.available else (
            "Optional. Without it, picture descriptions and similar texts are made with simple rules. "
            "Free and private: install Ollama (https://ollama.com) and run 'ollama pull gemma3:4b'. "
            f"Or put OPENROUTER_API_KEY=... or OPENAI_API_KEY=... into {user_env_file()}. "
            "PDFACCESSGURU_PRIVACY=local there makes sure nothing is sent to the internet."
        ),
        optional=True,
    ))
    return checks
