"""
Checks the installed browser app on this computer (used in CI on Windows, macOS and Linux):
starts `pdfaccessguru app --no-browser`, opens the page, uploads a PDF, waits until it is fixed,
downloads the result and closes the app. Uses only the Python standard library.

    python check_app.py some.pdf
"""

import json
import re
import subprocess
import sys
import time
import urllib.request
import uuid


def main(pdf_path: str) -> None:
    app = subprocess.Popen(["pdfaccessguru", "app", "--no-browser"], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, shell=sys.platform == "win32")
    url = None
    deadline = time.time() + 120
    while time.time() < deadline and url is None:
        line = app.stdout.readline()
        if not line and app.poll() is not None:
            break
        print("app:", line.rstrip())
        match = re.search(r"http://127\.0\.0\.1:\d+/[\w-]+/", line)
        url = match.group(0) if match else None
    assert url, "the app did not print its address"
    try:
        page = urllib.request.urlopen(url, timeout=30).read().decode()
        assert "<h1>PDFAccessGuru</h1>" in page, "the start page did not load"
        boundary = uuid.uuid4().hex
        data = open(pdf_path, "rb").read()
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="ai"\r\n\r\nnone\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.pdf"\r\n'
                f"Content-Type: application/pdf\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
        request = urllib.request.Request(url + "start", data=body, method="POST",
                                         headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        job_url = urllib.request.urlopen(request, timeout=60).geturl()
        assert "/job/" in job_url, f"the upload was not accepted: {job_url}"
        state = {}
        for _ in range(300):
            state = json.loads(urllib.request.urlopen(job_url + "/status", timeout=30).read())
            if state["state"] != "running":
                break
            time.sleep(2)
        assert state.get("state") == "done", f"the file was not fixed: {state}"
        result = urllib.request.urlopen(job_url, timeout=30).read().decode()
        links = re.findall(r'href="([^"]+)" download', result)
        assert len(links) == 3, "the result page does not offer the three downloads"
        pdf = urllib.request.urlopen(url.split("/", 3)[0] + "//" + url.split("/")[2] + links[0], timeout=60).read()
        assert pdf.startswith(b"%PDF"), "the downloaded file is not a PDF"
        print("browser app: page, upload, fix and download work")
        urllib.request.urlopen(urllib.request.Request(url + "quit", data=b"", method="POST"), timeout=30)
        app.wait(timeout=30)
    finally:
        if app.poll() is None:
            app.kill()


if __name__ == "__main__":
    main(sys.argv[1])
