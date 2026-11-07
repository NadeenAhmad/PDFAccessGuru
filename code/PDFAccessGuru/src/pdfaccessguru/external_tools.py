"""
Finds the external programs PDFAccessGuru needs: veraPDF (the PDF/UA checker) and the Java
runtime it runs on.

Programs installed by PDFAccessGuru itself live in the user's data folder (no admin rights
needed) and are preferred; otherwise the ones on the system PATH are used.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "pdfaccessguru"
VERAPDF_VERSION = "1.30.1"
# Free fonts with the same letter widths as Arial/Helvetica, Times New Roman/Times and
# Courier New/Courier. Used to embed fonts that a PDF uses but does not contain.
FONTS_VERSION = "2.1.5"


def tools_dir() -> Path:
    """
    Folder for programs downloaded by PDFAccessGuru (e.g. ~/.local/share/pdfaccessguru/tools).
    PDFACCESSGURU_TOOLS_DIR overrides it (used by tests and CI to install into a throwaway folder).
    """
    override = os.environ.get("PDFACCESSGURU_TOOLS_DIR")
    if override:
        return Path(override)
    return Path(user_data_dir(APP_NAME)) / "tools"


def _is_windows() -> bool:
    return platform.system() == "Windows"


def managed_java_home() -> Path:
    return tools_dir() / "java"


def managed_verapdf_dir() -> Path:
    return tools_dir() / "verapdf"


def managed_fonts_dir() -> Path:
    return tools_dir() / "fonts" / f"liberation-{FONTS_VERSION}"


def find_fallback_fonts() -> Path | None:
    """The folder with the Liberation fonts, if they are installed."""
    folder = managed_fonts_dir()
    return folder if (folder / "LiberationSans-Regular.ttf").is_file() else None


def find_java() -> Path | None:
    """The Java runtime: the one installed by PDFAccessGuru, else JAVA_HOME, else the PATH."""
    executable = "java.exe" if _is_windows() else "java"
    candidates = [managed_java_home() / "bin" / executable]
    if os.environ.get("JAVA_HOME"):
        candidates.append(Path(os.environ["JAVA_HOME"]) / "bin" / executable)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    found = shutil.which("java")
    return Path(found) if found else None


def find_verapdf() -> Path | None:
    """The veraPDF command: the one installed by PDFAccessGuru, else the one on the PATH."""
    script = "verapdf.bat" if _is_windows() else "verapdf"
    managed = managed_verapdf_dir() / script
    if managed.is_file():
        return managed
    found = shutil.which("verapdf")
    return Path(found) if found else None


def verapdf_environment() -> dict[str, str]:
    """Environment for running veraPDF: points it at the Java runtime installed by PDFAccessGuru, if any."""
    environment = dict(os.environ)
    java_home = managed_java_home()
    if (java_home / "bin").is_dir():
        environment["JAVA_HOME"] = str(java_home)
        environment["PATH"] = str(java_home / "bin") + os.pathsep + environment.get("PATH", "")
    return environment


def verapdf_version(verapdf: Path) -> str | None:
    """The installed veraPDF version, e.g. '1.30.1', or None if it does not run."""
    try:
        completed = subprocess.run(
            [str(verapdf), "--version"],
            capture_output=True, text=True, timeout=60, env=verapdf_environment(),
            shell=_is_windows(),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    for word in (completed.stdout or "").split():
        if word[:1].isdigit() and "." in word:
            return word
    return None
