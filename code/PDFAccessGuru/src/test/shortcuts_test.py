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
    text = "".join(p.read_text(errors="ignore") for p in ([target] if target.is_file() else target.rglob("*")) if p.is_file())
    assert str(launcher) in text
    if platform.system() == "Darwin":                  # the icon is in the app and named in Info.plist
        assert (target / "Contents" / "Resources" / "PDFAccessGuru.icns").stat().st_size > 10_000
        assert "<key>CFBundleIconFile</key><string>PDFAccessGuru</string>" in text
    else:
        assert "Icon=" in text and (shortcuts.ICONS / "app-icon.png").is_file()
    shortcuts.create_shortcut()                        # writing it again (refresh) works too
    shortcuts.remove_shortcut()
    assert not target.exists()


def test_uv_install_is_updated_with_uv(tmp_path, monkeypatch):
    (tmp_path / "uv-receipt.toml").write_text("")
    monkeypatch.setattr(updates.sys, "prefix", str(tmp_path))
    monkeypatch.setattr(updates.shutil, "which", lambda name: f"/usr/local/bin/{name}" if name == "uv" else None)
    assert updates.update_command() == ["/usr/local/bin/uv", "tool", "upgrade", "--no-build", "--refresh", "pdfaccessguru"]


@pytest.mark.skipif(platform.system() == "Windows", reason="Windows shortcuts need PowerShell; tested in CI on Windows")
def test_an_existing_shortcut_is_refreshed_once_per_version(tmp_path, monkeypatch):
    import json

    launcher = tmp_path / "bin" / "pdfaccessguru-app"
    launcher.parent.mkdir()
    launcher.write_text("#!/bin/sh\n")
    monkeypatch.setattr(shortcuts, "_app_launcher", lambda: launcher)
    monkeypatch.setenv("PDFACCESSGURU_SHORTCUT_DIR", str(tmp_path / "apps"))
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"tour_seen": True}))
    monkeypatch.setattr(updates, "settings_file", lambda: settings)
    made = []
    monkeypatch.setattr(shortcuts, "create_shortcut", lambda: made.append(1))
    shortcuts.refresh_after_update()
    assert made == []                                  # no shortcut yet: nothing is created
    shortcuts.shortcut_path().mkdir(parents=True)
    shortcuts.refresh_after_update()
    shortcuts.refresh_after_update()
    assert made == [1]                                 # once for this version
    assert json.loads(settings.read_text())["tour_seen"] is True
