"""Phase 7a: the accessible browser app and the report in plain language."""

from __future__ import annotations

import http.client
import json
import re
import threading
import time
import uuid
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from pdfaccessguru.webapp.markdown_html import markdown_to_html
from pdfaccessguru.webapp.server import App, _handler

RESOURCES = Path(__file__).resolve().parent / "resources"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("PDFACCESSGURU_AI", "none")
    application = App()
    application.server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(application))
    thread = threading.Thread(target=application.server.serve_forever, daemon=True)
    thread.start()
    yield application
    application.server.shutdown()
    application.server.server_close()


def _request(app, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", app.server.server_address[1], timeout=120)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    return response.status, dict(response.getheaders()), response.read()


def _upload(app, pdf: bytes | list[tuple[str, bytes]], **fields) -> tuple[int, dict]:
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for filename, data in ([("test.pdf", pdf)] if isinstance(pdf, bytes) else pdf):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                     f"Content-Type: application/pdf\r\n\r\n".encode() + data + b"\r\n")
    body = b"".join(parts) + f"--{boundary}--\r\n".encode()
    status, headers, _ = _request(app, "POST", f"/{app.token}/start", body,
                                  {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return status, headers


def test_the_app_only_answers_with_its_key(app):
    assert _request(app, "GET", "/")[0] == 403
    assert _request(app, "GET", "/wrong-key/")[0] == 403
    status, _, body = _request(app, "GET", f"/{app.token}/")
    assert status == 200


def test_every_field_of_the_form_has_a_label_and_the_page_has_a_language(app):
    page = _request(app, "GET", f"/{app.token}/?lang=de")[2].decode()
    assert '<html lang="de">' in page and page.count("<h1>") == 1
    inputs = set(re.findall(r'<(?:input|select)[^>]*\bid="([^"]+)"', page))
    labelled = set(re.findall(r'<label for="([^"]+)"', page))
    assert inputs and inputs <= labelled
    for described in re.findall(r'aria-describedby="([^"]+)"', page):
        assert f'id="{described}"' in page


def test_a_pdf_is_fixed_and_the_result_page_offers_the_downloads(app):
    pdf = (RESOURCES / "veraPDF_corpus/7.3-t01-fail-a.pdf").read_bytes()
    status, headers = _upload(app, pdf, review="on", language_ui="de")
    assert status == 303
    job_path = headers["Location"]
    assert _wait(app, job_path)["state"] == "done"
    page = _request(app, "GET", job_path)[2].decode()
    assert "<h1>Fertig: test.pdf</h1>" in page
    links = re.findall(r'href="([^"]+)" download', page)
    assert len(links) == 3
    status, headers, data = _request(app, "GET", links[0])
    assert status == 200 and data.startswith(b"%PDF") and "attachment" in headers["Content-Disposition"]
    # the app speaks German, but the report follows the PDF, which is English (Phase 7b)
    assert '<div lang="en" dir="ltr">' in page and "Picture without a description" in page
    assert 'name="language"' not in _request(app, "GET", f"/{app.token}/?lang=de")[2].decode()   # no question


def _wait(app, job_path):
    for _ in range(240):
        state = json.loads(_request(app, "GET", f"{job_path}/status")[2])
        if state["state"] != "running":
            return state
        time.sleep(1)
    return state


def test_several_files_are_fixed_one_after_the_other_and_offered_as_one_zip(app):
    import io
    import zipfile

    pdf = (RESOURCES / "veraPDF_corpus/7.3-t01-fail-a.pdf").read_bytes()
    status, headers = _upload(app, [("a.pdf", pdf), ("a.pdf", pdf)], language_ui="en")   # even with the same name
    assert status == 303
    assert _wait(app, headers["Location"])["state"] == "done"
    page = _request(app, "GET", headers["Location"])[2].decode()
    assert "<h1>Done: 2 files</h1>" in page and page.count("<details>") == 2
    assert page.count('class="badge') == 2                                    # one result badge per file
    zip_link = re.search(r'href="([^"]+PDFAccessGuru\.zip)" download', page).group(1)
    status, _, data = _request(app, "GET", zip_link)
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert status == 200 and "1 a/a_accessible.pdf" in names and "2 a/a_accessible.pdf" in names


def test_files_that_are_not_pdfs_are_refused_politely(app):
    status, _ = _upload(app, b"hello", language_ui="en")
    assert status == 400


def test_report_tables_have_header_cells_for_screen_readers():
    out = markdown_to_html("## Found\n\n| Problem | Found |\n|---|---:|\n| Picture without a description | 1 |\n")
    assert '<th scope="col">Problem</th>' in out and '<th scope="row">Picture without a description</th>' in out
    assert "<h2>Found</h2>" in out


def test_report_text_is_escaped():
    assert "&lt;script&gt;" in markdown_to_html("A <script>alert(1)</script> test")


def test_first_start_offers_to_download_the_helper_programs(app, monkeypatch):
    monkeypatch.setattr(app, "tools_missing", lambda: True)
    page = _request(app, "GET", f"/{app.token}/?lang=en")[2].decode()
    assert "Download them now" in page
    assert re.search(r'<button type="submit" class="big" disabled>Make the PDF accessible', page)


def test_a_new_version_is_announced_with_an_update_button(app):
    from pdfaccessguru.updates import UpdateInfo
    app.update = UpdateInfo(current="0.2.0", latest="0.3.0")
    page = _request(app, "GET", f"/{app.token}/?lang=en")[2].decode()
    assert "A new version of PDFAccessGuru is available: 0.3.0." in page and "Update now" in page


def test_font_and_icon_are_served_by_the_app_itself(app):
    status, headers, data = _request(app, "GET", f"/{app.token}/static/atkinson-hyperlegible-400-latin.woff2")
    assert status == 200 and headers["Content-Type"] == "font/woff2" and data.startswith(b"wOF2")
    status, headers, _ = _request(app, "GET", f"/{app.token}/static/icon.svg")
    assert status == 200 and headers["Content-Type"] == "image/svg+xml"
    assert _request(app, "GET", f"/{app.token}/static/../server.py")[0] == 404
    page = _request(app, "GET", f"/{app.token}/?lang=en")[2].decode()
    assert f"/{app.token}/static/atkinson-hyperlegible-400-latin.woff2" in page and 'aria-label="PDFAccessGuru, start page"' in page
