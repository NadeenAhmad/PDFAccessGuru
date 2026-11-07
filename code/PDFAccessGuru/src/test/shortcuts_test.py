import platform

import pytest

from pdfaccessguru import shortcuts, updates


@pytest.mark.skipif(platform.system() == "Windows", reason="Windows shortcuts need PowerShell; tested in CI on Windows")
def test_shortcut_is_created_and_removed(tmp_path, monkeypatch):
    launcher = tmp_path / "bin" / "pdfaccessguru-app"
    launcher.parent.mkdir()
    launcher.write_text("#!/bin/sh\n")
    monkeypatch.setattr(shortcuts, "_app_launcher", lambda: launcher)
    monkeypatch.setenv("PDFACCESSGURU_SHORTCUT_DIR", str(tmp_path / "apps"))

    target = shortcuts.create_shortcut()
    assert target.exists()
    text = "".join(p.read_text() for p in ([target] if target.is_file() else target.rglob("*") ) if p.is_file())
    assert str(launcher) in text
    shortcuts.remove_shortcut()
    assert not target.exists()


def test_uv_install_is_updated_with_uv(tmp_path, monkeypatch):
    (tmp_path / "uv-receipt.toml").write_text("")
    monkeypatch.setattr(updates.sys, "prefix", str(tmp_path))
    monkeypatch.setattr(updates.shutil, "which", lambda name: f"/usr/local/bin/{name}" if name == "uv" else None)
    assert updates.update_command() == ["/usr/local/bin/uv", "tool", "upgrade", "--no-build", "pdfaccessguru"]
