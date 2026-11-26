"""1.1.6: the start button says why it cannot be used yet, and the start page notices when the helper programs are ready."""

from __future__ import annotations

import json
import re
import threading
import time

from test.webapp_test import _request, app  # noqa: F401  (fixture)


def _button(page: str) -> str:
    return re.search(r'<button type="submit" class="big" id="start-button"[^>]*>', page).group(0)


def _reason(page: str) -> str | None:
    found = re.search(r'<p class="help start-reason" id="start-reason">([^<]*)</p>', page)
    return found.group(1) if found else None


def _status(app) -> dict:  # noqa: F811
    return json.loads(_request(app, "GET", f"/{app.token}/tools")[2])


def _wait(app, done) -> dict:  # noqa: F811
    deadline = time.time() + 10
    while not done(_status(app)) and time.time() < deadline:
        time.sleep(0.05)
    return _status(app)


def test_after_download_them_now_the_start_page_notices_when_the_helpers_are_ready(app, monkeypatch):  # noqa: F811
    missing, release = [True], threading.Event()

    def download(progress):
        progress("Downloading Java ...")
        release.wait(30)
        missing[0] = False

    monkeypatch.setattr("pdfaccessguru.tool_installer.ensure_tools", download)
    monkeypatch.setattr(app, "tools_missing", lambda: missing[0])
    status, headers, _ = _request(app, "POST", f"/{app.token}/install?lang=en")
    assert status == 303
    page = _request(app, "GET", headers["Location"])[2].decode()     # the page "Download them now" leads to
    assert "disabled" in _button(page) and 'aria-describedby="start-reason"' in _button(page)
    assert _reason(page) == "You can start as soon as the helper programs are downloaded."
    assert f'"url": "/{app.token}/tools"' in page                     # the page asks how far the download is
    assert ">Progress</a>" in page                                    # without JavaScript, this link still works
    assert _wait(app, lambda s: s["text"]) == {"state": "running", "text": "Downloading Java ...", "ready": False}

    release.set()
    assert _wait(app, lambda s: s["state"] != "running") == {"state": "done", "text": "", "ready": True}
    page = _request(app, "GET", f"/{app.token}/?lang=en")[2].decode()
    assert "disabled" not in _button(page) and "aria-describedby" not in _button(page)
    assert _reason(page) is None and f"/{app.token}/tools" not in page
    assert "The helper programs are ready." in page


def test_a_failed_download_is_reported_and_the_button_says_what_to_do(app, monkeypatch):  # noqa: F811
    def download(progress):
        raise OSError("no connection")

    monkeypatch.setattr("pdfaccessguru.tool_installer.ensure_tools", download)
    monkeypatch.setattr(app, "tools_missing", lambda: True)
    app.install_tools()
    assert _wait(app, lambda s: s["state"] != "running") == {"state": "failed", "text": "", "ready": False}
    page = _request(app, "GET", f"/{app.token}/?lang=de")[2].decode()   # the page reloads itself and shows this
    assert "Die Hilfsprogramme konnten nicht geladen werden: no connection" in page and "Jetzt herunterladen" in page
    assert "disabled" in _button(page) and 'aria-describedby="start-reason"' in _button(page)
    assert _reason(page) == "Laden Sie zuerst oben auf dieser Seite die Hilfsprogramme herunter."


def test_before_the_download_and_while_another_file_runs_the_reason_is_next_to_the_button(app, monkeypatch):  # noqa: F811
    monkeypatch.setattr(app, "tools_missing", lambda: True)
    page = _request(app, "GET", f"/{app.token}/?lang=en")[2].decode()
    assert _reason(page) == "First download the helper programs at the top of this page."
    assert f"/{app.token}/tools" not in page                          # nothing to wait for yet
    page = _request(app, "GET", f"/{app.token}/?lang=de")[2].decode()
    assert _reason(page) == "Laden Sie zuerst oben auf dieser Seite die Hilfsprogramme herunter."

    monkeypatch.setattr(app, "tools_missing", lambda: False)
    monkeypatch.setattr(app, "running_job", lambda: object())
    page = _request(app, "GET", f"/{app.token}/?lang=en")[2].decode()
    assert "disabled" in _button(page) and 'aria-describedby="start-reason"' in _button(page)
    assert _reason(page) == "Another file is being worked on. Please wait until it is finished."
