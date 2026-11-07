"""
Downloads and installs the two helper programs PDFAccessGuru needs, into the user's own
data folder (no admin rights, nothing changed outside that folder):

- a Java runtime (Eclipse Temurin JRE 21 from adoptium.net, about 42 MB), and
- veraPDF, the PDF/UA checker (about 33 MB), installed with that Java, and
- the Liberation fonts (about 2 MB, SIL Open Font License), used to embed fonts that a PDF
  uses but does not contain.

Every download is checked against a SHA-256 checksum before it is used: Java's checksum
comes from the Adoptium API, those of veraPDF and the fonts are fixed below.
"""

from __future__ import annotations

import hashlib
import platform
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path

import requests

from pdfaccessguru.external_tools import (
    FONTS_VERSION,
    VERAPDF_VERSION,
    find_fallback_fonts,
    find_java,
    find_verapdf,
    managed_fonts_dir,
    managed_java_home,
    managed_verapdf_dir,
    tools_dir,
    verapdf_version,
)

VERAPDF_URL = f"https://software.verapdf.org/rel/1.30/verapdf-greenfield-{VERAPDF_VERSION}-installer.zip"
VERAPDF_SHA256 = "9f03fc5da454348329f4054256351aa6c6a91683329978e8294f21fe8a5d7abc"
FONTS_URL = f"https://github.com/liberationfonts/liberation-fonts/files/7261482/liberation-fonts-ttf-{FONTS_VERSION}.tar.gz"
FONTS_SHA256 = "7191c669bf38899f73a2094ed00f7b800553364f90e2637010a69c0e268f25d0"
ADOPTIUM_ASSETS = "https://api.adoptium.net/v3/assets/latest/21/hotspot?os={os}&architecture={arch}&image_type=jre"

Progress = Callable[[str], None]


class ToolInstallError(Exception):
    """A helper program could not be installed. The message is meant for the user."""


def _platform_names() -> tuple[str, str]:
    system = {"Darwin": "mac", "Linux": "linux", "Windows": "windows"}.get(platform.system())
    machine = platform.machine().lower()
    arch = {"x86_64": "x64", "amd64": "x64", "arm64": "aarch64", "aarch64": "aarch64"}.get(machine)
    if system is None or arch is None:
        raise ToolInstallError(f"Automatic setup is not available for this computer ({platform.system()} {machine}).")
    return system, arch


def _download(url: str, target: Path, expected_sha256: str, progress: Progress, label: str) -> None:
    progress(f"Downloading {label} ...")
    digest = hashlib.sha256()
    try:
        with requests.get(url, stream=True, timeout=(15, 120)) as response:
            response.raise_for_status()
            with target.open("wb") as file:
                for chunk in response.iter_content(chunk_size=1 << 20):
                    file.write(chunk)
                    digest.update(chunk)
    except requests.RequestException as error:
        raise ToolInstallError(f"{label} could not be downloaded. Check the internet connection and try again. ({error})") from error
    if digest.hexdigest() != expected_sha256.lower():
        raise ToolInstallError(f"The download of {label} was damaged or changed (checksum mismatch). Please try again later.")


def _safe_extract(archive: Path, destination: Path) -> None:
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zipped:
            for name in zipped.namelist():
                if Path(name).is_absolute() or ".." in Path(name).parts:
                    raise ToolInstallError("The downloaded archive contains unsafe file names.")
            zipped.extractall(destination)
    else:
        with tarfile.open(archive) as tarred:
            tarred.extractall(destination, filter="data")


def install_java(progress: Progress = print) -> Path:
    """Install a Java runtime into the tools folder and return the java executable."""
    system, arch = _platform_names()
    try:
        assets = requests.get(ADOPTIUM_ASSETS.format(os=system, arch=arch), timeout=30).json()
        package = assets[0]["binary"]["package"]
    except (requests.RequestException, ValueError, KeyError, IndexError) as error:
        raise ToolInstallError("The Java download could not be found. Check the internet connection and try again.") from error

    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / package["name"]
        _download(package["link"], archive, package["checksum"], progress, f"Java ({round(package['size'] / 1e6)} MB)")
        progress("Unpacking Java ...")
        unpacked = Path(temporary) / "unpacked"
        _safe_extract(archive, unpacked)
        executable = "java.exe" if system == "windows" else "java"
        java_binaries = [path for path in unpacked.rglob(executable) if path.parent.name == "bin"]
        if not java_binaries:
            raise ToolInstallError("The Java download did not contain a Java program.")
        home = java_binaries[0].parent.parent
        target = managed_java_home()
        shutil.rmtree(target, ignore_errors=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(home), str(target))
    java = target / "bin" / executable
    if system != "windows":
        java.chmod(0o755)
    return java


def _answer_file(install_path: Path) -> str:
    """Answers for veraPDF's installer, so that it runs without questions."""
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<AutomatedInstallation langpack="eng">
  <com.izforge.izpack.panels.htmlhello.HTMLHelloPanel id="welcome"/>
  <com.izforge.izpack.panels.target.TargetPanel id="install_dir">
    <installpath>{install_path}</installpath>
  </com.izforge.izpack.panels.target.TargetPanel>
  <com.izforge.izpack.panels.packs.PacksPanel id="sdk_pack_select">
    <pack index="0" name="veraPDF GUI" selected="true"/>
    <pack index="1" name="veraPDF Batch files" selected="true"/>
    <pack index="2" name="veraPDF Validation model" selected="false"/>
    <pack index="3" name="veraPDF Documentation" selected="false"/>
    <pack index="4" name="veraPDF Sample Plugins" selected="false"/>
  </com.izforge.izpack.panels.packs.PacksPanel>
  <com.izforge.izpack.panels.install.InstallPanel id="install"/>
  <com.izforge.izpack.panels.finish.FinishPanel id="finish"/>
</AutomatedInstallation>
"""


def install_verapdf(java: Path, progress: Progress = print) -> Path:
    """Install veraPDF into the tools folder (using the given Java) and return its command."""
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "verapdf-installer.zip"
        _download(VERAPDF_URL, archive, VERAPDF_SHA256, progress, "veraPDF (33 MB)")
        progress("Installing veraPDF ...")
        _safe_extract(archive, Path(temporary))
        installer = next(Path(temporary).rglob("verapdf-izpack-installer-*.jar"), None)
        if installer is None:
            raise ToolInstallError("The veraPDF download did not contain its installer.")
        target = managed_verapdf_dir()
        shutil.rmtree(target, ignore_errors=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        answers = Path(temporary) / "auto-install.xml"
        answers.write_text(_answer_file(target), encoding="utf-8")
        try:
            subprocess.run([str(java), "-jar", str(installer), str(answers)],
                           check=True, capture_output=True, text=True, timeout=600)
        except (OSError, subprocess.SubprocessError) as error:
            raise ToolInstallError("veraPDF could not be installed.") from error

    verapdf = find_verapdf()
    if verapdf is None or managed_verapdf_dir() not in verapdf.parents:
        raise ToolInstallError("veraPDF was installed, but its start file is missing.")
    if platform.system() != "Windows":
        verapdf.chmod(0o755)
    return verapdf


def install_fonts(progress: Progress = print) -> Path:
    """Install the Liberation fonts into the tools folder and return their folder."""
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "liberation-fonts.tar.gz"
        _download(FONTS_URL, archive, FONTS_SHA256, progress, "fonts (2 MB)")
        _safe_extract(archive, Path(temporary))
        fonts = [path for path in Path(temporary).rglob("Liberation*.ttf")]
        if len(fonts) < 12:
            raise ToolInstallError("The font download did not contain the expected fonts.")
        target = managed_fonts_dir()
        shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True)
        for font in fonts + list(Path(temporary).rglob("LICENSE")):
            shutil.copy2(font, target / font.name)
    return target


def ensure_tools(progress: Progress = print, force: bool = False) -> None:
    """
    Make sure Java and the tested veraPDF version are available. Installs only what is missing
    (or, with force=True, the tested veraPDF version even if another version exists).
    """
    tools_dir().mkdir(parents=True, exist_ok=True)
    java = find_java()
    if java is None:
        java = install_java(progress)
    verapdf = find_verapdf()
    needs_verapdf = verapdf is None or (force and verapdf_version(verapdf) != VERAPDF_VERSION)
    if needs_verapdf:
        install_verapdf(java, progress)
    if find_fallback_fonts() is None:
        install_fonts(progress)
    progress("All helper programs are ready.")


def tools_missing() -> bool:
    return find_java() is None or find_verapdf() is None or find_fallback_fonts() is None
