import io
import zipfile

import pytest

from pdfaccessguru import external_tools, tool_installer
from pdfaccessguru.tool_installer import ToolInstallError


class _FakeResponse(io.BytesIO):
    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        while chunk := self.read(chunk_size):
            yield chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_platform_names(monkeypatch):
    monkeypatch.setattr(tool_installer.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(tool_installer.platform, "machine", lambda: "arm64")
    assert tool_installer._platform_names() == ("mac", "aarch64")
    monkeypatch.setattr(tool_installer.platform, "system", lambda: "Windows")
    monkeypatch.setattr(tool_installer.platform, "machine", lambda: "AMD64")
    assert tool_installer._platform_names() == ("windows", "x64")
    monkeypatch.setattr(tool_installer.platform, "machine", lambda: "riscv64")
    with pytest.raises(ToolInstallError):
        tool_installer._platform_names()


def test_download_with_wrong_checksum_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(tool_installer.requests, "get", lambda *a, **k: _FakeResponse(b"something else"))
    with pytest.raises(ToolInstallError, match="checksum"):
        tool_installer._download("https://example.invalid/x.zip", tmp_path / "x.zip", "00" * 32, lambda _: None, "test")


def test_archive_with_unsafe_paths_is_rejected(tmp_path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("../outside.txt", "x")
    with pytest.raises(ToolInstallError):
        tool_installer._safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "outside.txt").exists()


def test_tools_folder_can_be_redirected(tmp_path, monkeypatch):
    monkeypatch.setenv("PDFACCESSGURU_TOOLS_DIR", str(tmp_path))
    assert external_tools.tools_dir() == tmp_path
    assert external_tools.managed_verapdf_dir() == tmp_path / "verapdf"
