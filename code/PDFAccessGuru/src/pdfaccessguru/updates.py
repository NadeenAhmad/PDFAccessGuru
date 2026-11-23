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

import importlib.util
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
_INSTALLERS = "https://raw.githubusercontent.com/NadeenAhmad/PDFAccessGuru/main/code/PDFAccessGuru/installers/"
INSTALL_LINE_WINDOWS = f'powershell -ExecutionPolicy ByPass -c "irm {_INSTALLERS}install.ps1 | iex"'
INSTALL_LINE_UNIX = f"curl -LsSf {_INSTALLERS}install.sh | sh"
_CHECK_INTERVAL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class UpdateInfo:
    current: str
    latest: str
    release_notes_url: str = RELEASE_NOTES_URL


def _version_key(version: str) -> tuple[int, ...]:
    """1.1.0 → (1, 1, 0, 0); 1.1.0.post1 (a small fix of 1.1.0) → (1, 1, 0, 1)."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:\.post(\d+))?", version.split("+")[0])
    if match:
        return tuple(int(part or 0) for part in match.groups())
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
    if (prefix / "uv-receipt.toml").is_file():
        uv = find_uv()
        if uv:
            # --no-cache: ask PyPI again (uv 0.13 removed --refresh from "tool upgrade"; --no-cache works in all versions)
            return [uv, "tool", "upgrade", "--no-build", "--no-cache", PACKAGE]
        return installer_command()      # uv was removed: the installer puts uv back and installs the newest version
    pipx = shutil.which("pipx")
    if (prefix / "pipx_metadata.json").is_file() and pipx:
        return [pipx, "upgrade", PACKAGE]
    if "site-packages" in Path(__file__).resolve().as_posix():
        if importlib.util.find_spec("pip") is None:
            return None
        return [sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir", "--only-binary", ":all:", PACKAGE]
    return None  # running from a source checkout: update with git instead


def installer_command() -> list[str]:
    """The one-line installer from the README: installs uv if needed, then the newest PDFAccessGuru."""
    if platform.system() == "Windows":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "ByPass", "-c", f"irm {_INSTALLERS}install.ps1 | iex"]
    return ["/bin/sh", "-c", INSTALL_LINE_UNIX]


def install_line() -> str:
    """What people can paste into PowerShell (Windows) or Terminal (Mac, Linux) to install or update by hand."""
    return INSTALL_LINE_WINDOWS if platform.system() == "Windows" else INSTALL_LINE_UNIX


def find_uv() -> str | None:
    """
    uv on the PATH or in one of its usual folders. An app opened from the Finder or the Start menu often has a
    short PATH, so uv installed with the installer (~/.local/bin), cargo or Homebrew is looked for there too.
    """
    found = shutil.which("uv")
    if found:
        return found
    executable = "uv.exe" if platform.system() == "Windows" else "uv"
    home = Path.home()
    folders = [home / ".local" / "bin", home / ".cargo" / "bin"]
    if platform.system() == "Windows":
        folders.append(Path(os.environ.get("LOCALAPPDATA", str(home))) / "Programs" / "uv")
    else:
        folders += [Path("/opt/homebrew/bin"), Path("/usr/local/bin"), Path("/home/linuxbrew/.linuxbrew/bin")]
    for folder in folders:
        if (folder / executable).is_file():
            return str(folder / executable)
    return None


_default_uv = find_uv     # older name


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
    uv = find_uv()
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
    if command is None:
        return False
    if expected:
        _remember_started_update(expected)
    return start_after_exit(command, reopen_app, expected)


def _pending_file() -> Path:
    return Path(user_cache_dir(PACKAGE)) / "update_started.json"


def _remember_started_update(expected: str) -> None:
    try:
        _pending_file().parent.mkdir(parents=True, exist_ok=True)
        _pending_file().write_text(json.dumps({"version": expected, "at": time.time()}), encoding="utf-8")
    except OSError:
        pass


def failed_update() -> str | None:
    """
    The version an update was started for, if this program is still older (the update did not work), else None.
    Asked once when the app starts: the note is removed, so the message is shown only once.
    """
    try:
        expected = json.loads(_pending_file().read_text(encoding="utf-8")).get("version", "")
    except (OSError, ValueError, AttributeError):
        return None
    try:
        _pending_file().unlink()
    except OSError:
        pass
    return expected if isinstance(expected, str) and expected and is_newer(expected, __version__) else None


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
