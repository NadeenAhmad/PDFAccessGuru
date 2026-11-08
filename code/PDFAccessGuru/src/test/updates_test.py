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


def test_uv_asks_pypi_again_when_updating(monkeypatch, tmp_path):
    (tmp_path / "uv-receipt.toml").write_text("")
    monkeypatch.setattr(updates.sys, "prefix", str(tmp_path))
    monkeypatch.setattr(updates.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    assert updates.update_command() == ["/usr/bin/uv", "tool", "upgrade", "--no-build", "--refresh", "pdfaccessguru"]


def test_the_update_is_tried_again_while_the_new_version_is_not_on_the_server(monkeypatch):
    class Done:
        returncode = 0

    monkeypatch.setattr(updates, "update_command", lambda: ["update"])
    monkeypatch.setattr(updates.subprocess, "run", lambda *a, **k: Done())
    monkeypatch.setattr(updates, "UPDATE_WAIT_SECONDS", 0)
    said = []
    answers = iter([False, True])
    monkeypatch.setattr(updates, "installed_version_is", lambda expected: next(answers))
    assert updates.run_update_now("1.0.2", say=said.append) == "done" and len(said) == 1
    monkeypatch.setattr(updates, "installed_version_is", lambda expected: False)
    assert updates.run_update_now("1.0.2", say=said.append) == "not_ready"
    assert len(said) == 1 + updates.UPDATE_ATTEMPTS - 1


def _after_exit_line(monkeypatch, command, **options) -> str:
    """The shell line start_after_exit would run (macOS/Linux), without starting it."""
    started = []
    with monkeypatch.context() as patch:
        patch.setattr(updates.platform, "system", lambda: "Darwin")
        patch.setattr(updates.subprocess, "Popen", lambda args, **kwargs: started.append(args))
        updates.start_after_exit(command, **options)
    return started[0][2]


def test_the_update_after_closing_the_app_tries_again_and_reopens_it(monkeypatch, tmp_path):
    import subprocess

    monkeypatch.setattr(updates, "UPDATE_WAIT_SECONDS", 0)
    log = tmp_path / "runs.txt"
    command = ["sh", "-c", f"echo run >> '{log}'"]
    line = _after_exit_line(monkeypatch, command, reopen_app=True, expected="99.0.0")
    assert line.startswith("sleep 2; n=0; while :;") and line.endswith("(pdfaccessguru-app >/dev/null 2>&1 &)")
    loop = line[len("sleep 2; "):line.index("; (pdfaccessguru-app")]
    subprocess.run(["/bin/sh", "-c", loop], timeout=120)        # the real loop, with a stand-in update command
    assert log.read_text().count("run") == updates.UPDATE_ATTEMPTS          # 99.0.0 never arrives: tried 4 times
    log.unlink()
    line = _after_exit_line(monkeypatch, command, expected="0.0.1")
    subprocess.run(["/bin/sh", "-c", line[len("sleep 2; "):]], timeout=120)
    assert log.read_text().count("run") == 1                                  # already new enough: once
