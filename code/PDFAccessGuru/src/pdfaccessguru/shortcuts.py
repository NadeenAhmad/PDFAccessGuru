"""
Creates (or removes) a shortcut that opens the PDFAccessGuru app:

- Windows: an entry in the Start menu,
- macOS:   "PDFAccessGuru" in the user's Applications folder,
- Linux:   an entry in the app menu.

The shortcut starts the `pdfaccessguru-app` program that the installer put on the computer,
and shows the PDFAccessGuru icon (webapp/static/app-icon.*). It is created locally by
PDFAccessGuru itself, so the system shows no "downloaded from the internet" warning.
PDFACCESSGURU_SHORTCUT_DIR redirects the target folder (used by tests).
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

NAME = "PDFAccessGuru"
ICONS = Path(__file__).resolve().parent / "webapp" / "static"


def _app_launcher() -> Path:
    """The pdfaccessguru-app program next to the running Python (or on the PATH)."""
    executable = "pdfaccessguru-app.exe" if platform.system() == "Windows" else "pdfaccessguru-app"
    for folder in (Path(sys.executable).parent, Path(sys.executable).parent / "Scripts"):
        if (folder / executable).is_file():
            return folder / executable
    found = shutil.which("pdfaccessguru-app")
    if found:
        return Path(found)
    raise FileNotFoundError("The program 'pdfaccessguru-app' was not found. Please run the installer again.")


def shortcut_path() -> Path:
    override = os.environ.get("PDFACCESSGURU_SHORTCUT_DIR")
    system = platform.system()
    if system == "Windows":
        folder = Path(override) if override else Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        return folder / f"{NAME}.lnk"
    if system == "Darwin":
        folder = Path(override) if override else Path.home() / "Applications"
        return folder / f"{NAME}.app"
    folder = Path(override) if override else Path.home() / ".local" / "share" / "applications"
    return folder / "pdfaccessguru.desktop"


def create_shortcut() -> Path:
    launcher = _app_launcher()
    target = shortcut_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    system = platform.system()
    if system == "Windows":
        script = (
            "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:PAG_LNK); "
            "$s.TargetPath = $env:PAG_TARGET; $s.Description = 'Make PDF files accessible'; "
            "$s.IconLocation = $env:PAG_ICON + ',0'; $s.Save()"
        )
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            check=True, env={**os.environ, "PAG_LNK": str(target), "PAG_TARGET": str(launcher),
                             "PAG_ICON": str(ICONS / "app-icon.ico")},
        )
    elif system == "Darwin":
        # Written in place (not deleted first), so it can also be refreshed while the app runs.
        macos = target / "Contents" / "MacOS"
        macos.mkdir(parents=True, exist_ok=True)
        resources = target / "Contents" / "Resources"
        resources.mkdir(exist_ok=True)
        shutil.copyfile(ICONS / "app-icon.icns", resources / f"{NAME}.icns")
        start = macos / NAME
        # Starts the app in the background and ends at once: the app has no window of its own, so
        # an icon that stayed in the Dock would do nothing when clicked. Every click runs this
        # again, and a running app is simply shown again in the browser.
        start.write_text(f'#!/bin/sh\nnohup "{launcher}" "$@" >/dev/null 2>&1 &\n', encoding="utf-8")
        start.chmod(0o755)
        (target / "Contents" / "Info.plist").write_text(
            f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>{NAME}</string>
  <key>CFBundleDisplayName</key><string>{NAME}</string>
  <key>CFBundleIdentifier</key><string>org.pdfaccessguru.app</string>
  <key>CFBundleExecutable</key><string>{NAME}</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleIconFile</key><string>{NAME}</string>
  <key>CFBundleShortVersionString</key><string>{_version()}</string>
</dict></plist>
""",
            encoding="utf-8",
        )
        os.utime(target)                      # so Finder and the Dock show the new icon
    else:
        target.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={NAME}\n"
            "Comment=Make PDF files accessible\n"
            f'Exec="{launcher}"\n'
            f'Icon={ICONS / "app-icon.png"}\n'
            "Terminal=false\n"
            "Categories=Office;Utility;\n",
            encoding="utf-8",
        )
    return target


def _version() -> str:
    from pdfaccessguru import __version__

    return __version__


def refresh_after_update() -> None:
    """
    Write an existing shortcut again, once per version: after an update it then has the newest
    icon and points to the newest program. Never stops the app from starting.
    """
    from pdfaccessguru.updates import settings_file

    try:
        if not shortcut_path().exists():
            return
        path = settings_file()
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            settings = {}
        if not isinstance(settings, dict) or settings.get("shortcut_version") == _version():
            return
        create_shortcut()
        settings["shortcut_version"] = _version()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=1), encoding="utf-8")
    except Exception:                         # a missing icon must never keep the app from opening
        pass


def remove_shortcut() -> None:
    target = shortcut_path()
    if target.is_dir():
        shutil.rmtree(target, ignore_errors=True)
    elif target.exists():
        target.unlink()
