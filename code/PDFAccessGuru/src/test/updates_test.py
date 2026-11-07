import os
import time

from pdfaccessguru import updates


class _Reply:
    def __init__(self, version):
        self._version = version

    def json(self):
        return {"info": {"version": self._version}}


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(updates, "user_cache_dir", lambda _name: str(tmp_path / "cache"))
    monkeypatch.setattr(updates, "user_config_dir", lambda _name: str(tmp_path / "config"))
    monkeypatch.delenv("PDFACCESSGURU_NO_UPDATE_CHECK", raising=False)


def test_version_comparison():
    assert updates.is_newer("0.3.0", "0.2.0")
    assert updates.is_newer("1.0.0", "0.10.2")
    assert not updates.is_newer("0.2.0", "0.2.0")
    assert not updates.is_newer("0.1.9", "0.2.0")


def test_newer_version_is_reported_once_a_day(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(updates, "__version__", "0.2.0")
    monkeypatch.setattr(updates.requests, "get", lambda *a, **k: _Reply("0.3.0"))

    info = updates.check_for_update()
    assert info is not None and info.latest == "0.3.0"
    assert updates.check_for_update() is None              # already checked today
    assert updates.check_for_update(force=True) is not None


def test_check_can_be_switched_off(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setattr(updates.requests, "get", lambda *a, **k: _Reply("99.0.0"))
    monkeypatch.setenv("PDFACCESSGURU_NO_UPDATE_CHECK", "1")
    assert updates.check_for_update() is None


def test_no_connection_is_not_an_error(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)

    def offline(*_args, **_kwargs):
        raise OSError("no network")

    monkeypatch.setattr(updates.requests, "get", offline)
    assert updates.check_for_update(force=True) is None


def test_source_checkout_is_never_updated_with_pip(monkeypatch):
    monkeypatch.setattr(updates.sys, "prefix", "/home/dev/project/.venv")
    assert updates.update_command() is None
