"""
Update check and update for PDFAccessGuru.

- The check asks PyPI (where the tool is installed from) for the newest version number.
  Nothing about the user or their documents is sent. It runs at most once a day.
- It can be switched off with PDFACCESSGURU_NO_UPDATE_CHECK=1 or with
  "check_for_updates": false in the settings file.
- The update runs the command of the installer that was used (uv, pipx or pip). On Windows a
  running program cannot replace its own files, so the update starts right after the app or
  command has closed, and the app is opened again afterwards.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from platformdirs import user_cache_dir, user_config_dir

from pdfaccessguru import __version__

PACKAGE = "pdfaccessguru"
VERSION_URL = f"https://pypi.org/pypi/{PACKAGE}/json"
RELEASE_NOTES_URL = "https://github.com/NadeenAhmad/PDFAccessGuru/releases"
_CHECK_INTERVAL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class UpdateInfo:
    current: str
    latest: str
    release_notes_url: str = RELEASE_NOTES_URL


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version.split("+")[0])[:3])


def is_newer(latest: str, current: str) -> bool:
    return _version_key(latest) > _version_key(current)


def settings_file() -> Path:
    return Path(user_config_dir(PACKAGE)) / "settings.json"


def update_check_enabled() -> bool:
    if os.environ.get("PDFACCESSGURU_NO_UPDATE_CHECK"):
        return False
    try:
        return bool(json.loads(settings_file().read_text(encoding="utf-8")).get("check_for_updates", True))
    except (OSError, ValueError):
        return True


def _stamp_file() -> Path:
    return Path(user_cache_dir(PACKAGE)) / "last_update_check"


def check_for_update(force: bool = False, timeout: float = 3.0) -> UpdateInfo | None:
    """
    Return information about a newer version, or None (no newer version, check switched off,
    already checked today, or no connection). Never raises.
    """
    if not force:
        if not update_check_enabled():
            return None
        try:
            if time.time() - _stamp_file().stat().st_mtime < _CHECK_INTERVAL_SECONDS:
                return None
        except OSError:
            pass
    try:
        latest = requests.get(VERSION_URL, timeout=timeout).json()["info"]["version"]
    except Exception:
        return None
    try:
        _stamp_file().parent.mkdir(parents=True, exist_ok=True)
        _stamp_file().touch()
    except OSError:
        pass
    if is_newer(latest, __version__):
        return UpdateInfo(current=__version__, latest=latest)
    return None


def update_command() -> list[str] | None:
    """The command that updates this installation, depending on how it was installed."""
    prefix = Path(sys.prefix)
    # uv and pipx leave a receipt file in every tool environment they create.
    uv = shutil.which("uv") or _default_uv()
    if (prefix / "uv-receipt.toml").is_file() and uv:
        return [uv, "tool", "upgrade", "--no-build", "--refresh", PACKAGE]     # --refresh: ask PyPI again
    pipx = shutil.which("pipx")
    if (prefix / "pipx_metadata.json").is_file() and pipx:
        return [pipx, "upgrade", PACKAGE]
    if "site-packages" in Path(__file__).resolve().as_posix():
        return [sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir", "--only-binary", ":all:", PACKAGE]
    return None  # running from a source checkout: update with git instead


def _default_uv() -> str | None:
    """uv in its default install folder (the installer puts it there; it may not be on the PATH yet)."""
    executable = "uv.exe" if platform.system() == "Windows" else "uv"
    candidate = Path.home() / ".local" / "bin" / executable
    return str(candidate) if candidate.is_file() else None


def manual_update_hint() -> str:
    return (
        "To update, run this command in a terminal: uv tool upgrade pdfaccessguru "
        "(or install again with the one-line installer from the website)."
    )


# Right after a release, PyPI's servers can still give out the old version list for a few
# minutes. So after updating, the installed version is checked, and the update is tried again.
UPDATE_ATTEMPTS = 4
UPDATE_WAIT_SECONDS = 60
_INSTALLED_VERSION = (f"import importlib.metadata as m, sys; t = lambda s: tuple(int(x) for x in "
                      f"s.split('+')[0].split('.')[:3] if x.isdigit()); "
                      f"sys.exit(0 if t(m.version('{PACKAGE}')) >= t(sys.argv[1]) else 1)")


def installed_version_is(expected: str) -> bool:
    """True if the version installed now is `expected` or newer (this process still runs the old one)."""
    try:
        return subprocess.run([sys.executable, "-c", _INSTALLED_VERSION, expected], timeout=120).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def run_update_now(expected: str | None = None, say=print) -> str:
    """
    Update in this process (macOS/Linux command line). Returns "done", "not_ready" (the new
    version is not on the server yet; tried for a few minutes) or "failed".
    """
    command = update_command()
    if command is None:
        return "failed"
    for attempt in range(UPDATE_ATTEMPTS):
        if subprocess.run(command).returncode != 0:
            return "failed"
        if expected is None or installed_version_is(expected):
            return "done"
        if attempt < UPDATE_ATTEMPTS - 1:
            say("The new version is not ready on the server yet. Trying again in a minute ...")
            time.sleep(UPDATE_WAIT_SECONDS)
    return "not_ready"


def uninstall_command() -> list[str] | None:
    """The command that removes this installation, depending on how it was installed."""
    prefix = Path(sys.prefix)
    uv = shutil.which("uv") or _default_uv()
    if (prefix / "uv-receipt.toml").is_file() and uv:
        return [uv, "tool", "uninstall", PACKAGE]
    pipx = shutil.which("pipx")
    if (prefix / "pipx_metadata.json").is_file() and pipx:
        return [pipx, "uninstall", PACKAGE]
    if "site-packages" in Path(__file__).resolve().as_posix():
        return [sys.executable, "-m", "pip", "uninstall", "-y", PACKAGE]
    return None


def start_update_after_exit(reopen_app: bool, expected: str | None = None) -> bool:
    """
    Start the update in a separate process that waits a moment for this program to close,
    then updates and (optionally) opens the app again. On macOS and Linux it checks the
    installed version afterwards and tries again for a few minutes if the new version was not
    on the server yet. Returns False if no update command exists.
    """
    command = update_command()
    return command is not None and start_after_exit(command, reopen_app, expected)


def start_after_exit(command: list[str], reopen_app: bool = False, expected: str | None = None) -> bool:
    """Run a command in a separate process a few seconds after this program has closed."""
    if platform.system() == "Windows":
        reopen = " & start \"\" pdfaccessguru-app" if reopen_app else ""
        line = "timeout /t 3 /nobreak >nul & " + subprocess.list2cmdline(command) + reopen
        subprocess.Popen(["cmd", "/c", line], creationflags=0x00000008 | 0x00000200)  # DETACHED, NEW_PROCESS_GROUP
    else:
        run = " ".join(_shell_quote(part) for part in command)
        if expected:
            check = " ".join(_shell_quote(part) for part in (sys.executable, "-c", _INSTALLED_VERSION, expected))
            run = (f"n=0; while :; do {run}; {check} && break; n=$((n+1)); "
                   f"[ $n -ge {UPDATE_ATTEMPTS} ] && break; sleep {UPDATE_WAIT_SECONDS}; done")
        reopen = "; (pdfaccessguru-app >/dev/null 2>&1 &)" if reopen_app else ""
        line = "sleep 2; " + run + reopen
        subprocess.Popen(["/bin/sh", "-c", line], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def _shell_quote(text: str) -> str:
    return "'" + text.replace("'", "'\"'\"'") + "'"
