"""1.1.4: Update now shows its progress in the same tab, and the new version opens there."""

from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer

from pdfaccessguru import __version__, updates
from pdfaccessguru.webapp import server as server_module
from pdfaccessguru.webapp.server import App, _handler
from test.webapp_test import _request, app  # noqa: F401  (fixture)


def test_the_app_tells_which_version_answers(app):  # noqa: F811
    status, headers, body = _request(app, "GET", f"/{app.token}/version")
    assert status == 200 and json.loads(body) == {"version": __version__}


def test_update_now_shows_steps_and_progress_and_reopens_at_the_same_address(monkeypatch):
    started = {}

    def fake_start(**options):
        started.update(options)
        return True

    monkeypatch.setattr(updates, "start_update_after_exit", fake_start)
    application = App()
    application.update = updates.UpdateInfo(current=__version__, latest="99.0.0")
    application.server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(application))
    threading.Thread(target=application.server.serve_forever, daemon=True).start()
    page = _request(application, "POST", f"/{application.token}/update?lang=en", b"",
                    {"Content-Type": "application/x-www-form-urlencoded"})[2].decode()
    application.server.server_close()
    assert started == {"reopen_app": True, "expected": "99.0.0",
                       "reopen_at": (application.server.server_address[1], application.token)}
    assert "Updating PDFAccessGuru to version 99.0.0" in page and '<progress id="up-bar"' in page
    for step in ("Closing this version", "Downloading and installing the new version", "Opening the new version"):
        assert step in page
    assert '"typical": 45' in page and "version" in page and 'role="status"' in page


def test_the_new_version_takes_over_the_waiting_address(monkeypatch):
    monkeypatch.setenv("PDFACCESSGURU_REOPEN", "51234:" + "a" * 24)
    assert server_module._reopen_request() == (51234, "a" * 24)
    assert "PDFACCESSGURU_REOPEN" not in server_module.os.environ                 # not passed on to later programs
    for wrong in ("80:" + "a" * 24, "51234:short", "x:y", ""):
        monkeypatch.setenv("PDFACCESSGURU_REOPEN", wrong)
        assert server_module._reopen_request() is None


def test_the_updater_reopens_the_app_by_its_full_path_at_the_same_address(monkeypatch, tmp_path):
    launcher = tmp_path / "pdfaccessguru-app"
    launcher.write_text("")
    monkeypatch.setattr(updates.sys, "executable", str(tmp_path / "python"))
    monkeypatch.setattr(updates.platform, "system", lambda: "Darwin")
    lines = []
    monkeypatch.setattr(updates.subprocess, "Popen", lambda command, **options: lines.append(command[-1]))
    updates.start_after_exit(["uv", "tool", "upgrade"], reopen_app=True, expected="9.9.9", reopen_at=(51234, "k" * 24))
    assert f"PDFACCESSGURU_REOPEN='51234:{'k' * 24}' '{launcher}'" in lines[0]


def test_after_the_update_the_page_says_it_worked(app):  # noqa: F811
    page = _request(app, "GET", f"/{app.token}/?lang=en&updated={__version__}")[2].decode()
    assert f"PDFAccessGuru was updated to version {__version__}." in page
    page = _request(app, "GET", f"/{app.token}/?lang=en&updated=0.0.1")[2].decode()
    assert "was updated to version" not in page                                   # only the version that runs
