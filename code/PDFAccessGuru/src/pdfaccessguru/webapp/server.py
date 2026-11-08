"""
The browser app (Phase 7a): a small web server on this computer only (127.0.0.1), with a random
key in every address, so no website and no other computer can use it. One job runs at a time; a
job can have several files (Phase 7b), which are fixed one after the other. Each report is in the
language of its PDF. Started with `pdfaccessguru app`; it opens the browser by itself.
"""

from __future__ import annotations

import email.parser
import email.policy
import html
import json
import os
import secrets
import shutil
import tempfile
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from pdfaccessguru.webapp.markdown_html import markdown_to_html
from pdfaccessguru.webapp.pages import TEXT, choice, page, tour

MAX_UPLOAD = 300 * 1024 * 1024          # 300 MB
STATIC = Path(__file__).with_name("static")
STATIC_FILES = {path.name for path in STATIC.iterdir()} if STATIC.is_dir() else set()
IDLE_SHUTDOWN = 2 * 60 * 60              # the app stops after 2 hours without any use


@dataclass
class Result:
    """One file of a job."""
    name: str
    source: Path
    state: str = "waiting"               # waiting, running, done, error, stopped
    error: str = ""
    passes: bool = False
    fixed: int = 0
    still_open: int = 0
    to_check: int = 0
    language: str = "en"                 # language of the report (= of the PDF)
    files: dict[str, str] = field(default_factory=dict)    # kind (pdf, report_pdf, report_md) -> key in Job.files
    report_html: str = ""
    report: dict | None = None           # the pipeline report; the user's review is added to it
    review_list: bool = False            # the user asked for the review list in the report
    checked: set[str] = field(default_factory=set)          # groups of texts the user marked as checked
    preview: str = ""                                       # "what a screen reader reads", made on request


@dataclass
class Job:
    job_id: str
    name: str                            # the file name, or "3 files"
    language: str                        # language of the app pages
    folder: Path
    results: list[Result] = field(default_factory=list)
    text: str = ""
    fraction: float = 0.0
    state: str = "running"               # running, done, error, stopped
    error: str = ""
    cancel: threading.Event = field(default_factory=threading.Event)
    files: dict[str, Path] = field(default_factory=dict)


class App:
    def __init__(self) -> None:
        self.token = secrets.token_urlsafe(18)
        self.work = Path(tempfile.mkdtemp(prefix="pdfaccessguru-app-"))
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.last_use = time.time()
        self.server: ThreadingHTTPServer | None = None
        self.tools_state = "idle"                 # idle, running, done, failed
        self.tools_text = ""
        self.update = None                        # UpdateInfo, if a newer version exists
        threading.Thread(target=self._check_update, daemon=True).start()

    def _check_update(self) -> None:
        try:
            from pdfaccessguru.updates import check_for_update
            self.update = check_for_update()
        except Exception:
            self.update = None

    def tools_missing(self) -> bool:
        try:
            from pdfaccessguru.tool_installer import tools_missing
            return tools_missing()
        except Exception:
            return False

    def install_tools(self) -> None:
        if self.tools_state == "running":
            return
        self.tools_state, self.tools_text = "running", ""

        def run() -> None:
            from pdfaccessguru.tool_installer import ensure_tools
            try:
                ensure_tools(progress=lambda text: setattr(self, "tools_text", text))
                self.tools_state = "done"
            except Exception as error:
                self.tools_state, self.tools_text = "failed", str(error)

        threading.Thread(target=run, daemon=True).start()

    def running_job(self) -> Job | None:
        return next((job for job in self.jobs.values() if job.state == "running"), None)

    # --- the work ------------------------------------------------------------------------------

    def start_job(self, uploads: list[tuple[str, bytes]], options: dict[str, str]) -> Job:
        language = "de" if options.get("language_ui") == "de" else "en"
        job_id = secrets.token_hex(6)
        folder = self.work / job_id
        folder.mkdir()
        results = []
        for number, (upload_name, data) in enumerate(uploads, start=1):
            name = Path(upload_name).name or "document.pdf"
            source = folder / str(number) / name           # own folder: two uploads may have the same name
            source.parent.mkdir()
            source.write_bytes(data)
            results.append(Result(name, source))
        title = results[0].name if len(results) == 1 else TEXT[language]["n_files"].format(n=len(results))
        job = Job(job_id, title, language, folder, results)
        self.jobs[job_id] = job
        threading.Thread(target=self._run, args=(job, options), daemon=True).start()
        return job

    def _run(self, job: Job, options: dict[str, str]) -> None:
        ai = options.get("ai", "none")
        if ai == "cloud":                                   # the only choice that sends anything away
            os.environ["PDFACCESSGURU_AI"] = "openrouter" if os.environ.get("OPENROUTER_API_KEY") else "openai"
            os.environ.pop("PDFACCESSGURU_PRIVACY", None)
        else:                                               # Ollama or simple rules: nothing leaves the computer
            os.environ["PDFACCESSGURU_AI"] = "ollama" if ai == "ollama" else "none"
            os.environ["PDFACCESSGURU_PRIVACY"] = "local"
        t = TEXT[job.language]
        count = len(job.results)
        for index, result in enumerate(job.results):
            if job.cancel.is_set():
                result.state = "stopped"
                continue
            result.state = "running"

            def progress(text: str, fraction: float, index=index, result=result) -> None:
                prefix = t["file_n_of"].format(n=index + 1, total=count, name=result.name) + ": " if count > 1 else ""
                job.text, job.fraction = prefix + text, (index + fraction) / count

            try:
                self._fix_one(job, index + 1, result, options, progress)
                result.state = "done"
            except InterruptedError:
                result.state = "stopped"
            except Exception as error:                     # shown to the user in plain words
                result.state, result.error = "error", str(error) or error.__class__.__name__
        if count > 1 and any(result.state == "done" for result in job.results):
            self._zip_all(job)
        states = {result.state for result in job.results}
        if "done" in states:
            job.state = "done"
        elif "error" in states:
            job.state = "error"
            job.error = next(result.error for result in job.results if result.state == "error")
        else:
            job.state = "stopped"
        job.fraction, job.text = 1.0, ""

    def _fix_one(self, job: Job, number: int, result: Result, options: dict[str, str], progress) -> None:
        from pdfaccessguru.pipeline.pipeline import run_pipeline
        from pdfaccessguru.reporting import build_report_metrics
        from pdfaccessguru.reporting.report_language import report_language

        source = result.source
        output = source.with_name(f"{source.stem}_accessible.pdf")
        report = run_pipeline(str(source), str(output), progress_callback=progress, cancel_event=job.cancel,
                              owner_password=options.get("password") or None,
                              fix_contrast=options.get("fix_contrast") == "on")
        progress(TEXT[job.language]["writing_report"], 0.97)
        job.files[f"{number}/{output.name}"] = output
        result.files["pdf"] = f"{number}/{output.name}"
        result.report, result.review_list = report, options.get("review") == "on"
        result.language = report_language(output)
        metrics = build_report_metrics(report)
        result.passes, result.fixed, result.still_open = metrics.passes_verapdf, metrics.corrected_count, metrics.remaining_count
        self._write_report(job, number, result)

    def _write_report(self, job: Job, number: int, result: Result) -> None:
        """
        The report (text, PDF, pictures of the review list) and its view on the result page, from
        result.report. Written again whenever the user saves on the review page, so the report
        always includes their changes (Phase 12c). The review list always shows the pictures.
        """
        from pdfaccessguru.reporting import (
            build_customer_report_images, build_customer_report_markdown, build_customer_report_pdf,
        )
        from pdfaccessguru.reporting.report_language import text_direction
        from pdfaccessguru.reporting.review_list import build_review_groups

        report, review, source = result.report, result.review_list, result.source
        markdown = build_customer_report_markdown(report, review, review, result.language)
        report_md = source.with_name(f"{source.stem}_report.md")
        report_md.write_text(markdown, encoding="utf-8")
        report_pdf = source.with_name(f"{source.stem}_report.pdf")
        report_pdf.write_bytes(build_customer_report_pdf(report, review, review, result.language))
        for relative, data in (build_customer_report_images(report) if review else {}).items():
            target = source.parent / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            job.files[f"{number}/{relative}"] = target
        for kind, path in (("report_pdf", report_pdf), ("report_md", report_md)):
            job.files[f"{number}/{path.name}"] = path
            result.files[kind] = f"{number}/{path.name}"
        result.to_check = sum(len(group.pending) for group in build_review_groups(report))   # as in the report
        prefix = f"/{self.token}/job/{job.job_id}/file/{number}/"
        body = markdown.split("\n", 1)[1] if markdown.startswith("# ") else markdown   # the page has its own title
        offset = 1 if len(job.results) == 1 else 2
        inner = markdown_to_html(body, lambda path: prefix + quote(path), heading_offset=offset)
        result.report_html = f'<div lang="{result.language}" dir="{text_direction(result.language)}">{inner}</div>'

    def _zip_all(self, job: Job) -> None:
        """All new files and reports of a job in one ZIP, one folder per file."""
        import zipfile

        archive = job.folder / "PDFAccessGuru.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for key, path in job.files.items():
                number, _, relative = key.partition("/")
                if not relative:                           # the ZIP file itself
                    continue
                result = job.results[int(number) - 1]
                bundle.write(path, f"{number} {Path(result.name).stem}/{relative}")
        job.files["PDFAccessGuru.zip"] = archive

    # --- pages ---------------------------------------------------------------------------------

    def form(self, language: str, message: str = "") -> bytes:
        t = TEXT[language]
        other = "de" if language == "en" else "en"
        busy = self.running_job() is not None
        alert = f'<div class="alert" role="alert">{html.escape(message)}</div>' if message else ""
        notices = ""
        if self.update is not None:
            notices += f"""<section class="status" aria-labelledby="update-text"><p id="update-text">{html.escape(t['update'].format(version=self.update.latest))}</p>
<form method="post" action="/{self.token}/update"><p class="help" id="update-help">{t['update_help']}</p>
<p><button type="submit" aria-describedby="update-help">{t['update_button']}</button></p></form></section>"""
        tools_needed = self.tools_missing()
        if self.tools_state == "running":
            notices += f'<div class="status" role="status">{html.escape(t["tools_working"].format(text=self.tools_text or "…"))}</div>'
            notices += f'<p><a href="/{self.token}/?lang={language}">{t["progress_label"]}</a></p>'
        elif self.tools_state == "failed":
            notices += f'<div class="alert" role="alert">{html.escape(t["tools_failed"].format(error=self.tools_text))}</div>'
        elif self.tools_state == "done":
            notices += f'<div class="status" role="status">{t["tools_done"]}</div>'
        if tools_needed and self.tools_state != "running":
            notices += f"""<section class="status" aria-labelledby="tools-text"><p id="tools-text">{t['tools_needed']}</p>
<form method="post" action="/{self.token}/install?lang={language}"><p><button type="submit">{t['tools_button']}</button></p></form></section>"""
        busy = busy or tools_needed
        body = f"""
<h1>{t['hero_title']}</h1>
<p class="lead">{t['intro']}</p>
<ul class="promises"><li>{t['promise_local']}</li><li>{t['promise_original']}</li><li>{t['promise_standard']}</li><li>{t['promise_free']}</li></ul>
{alert}
{notices}
{f'<div class="status" role="status">{t["busy"]}</div>' if busy and not tools_needed else ''}
<form method="post" action="/{self.token}/start" enctype="multipart/form-data">
<input type="hidden" name="language_ui" value="{language}">
<fieldset class="card" id="tour-1"><legend><h2><span class="num" aria-hidden="true">1</span>{t['file_legend'][3:]}</h2></legend>
  <div class="drop">
  <label for="file">{t['file_label']}</label>
  <p class="help" id="file-help">{t['file_help']}</p>
  <input type="file" id="file" name="file" accept="application/pdf,.pdf" multiple required aria-describedby="file-help">
  </div>
</fieldset>
<fieldset class="card" id="tour-2" aria-describedby="ai-intro"><legend><h2><span class="num" aria-hidden="true">2</span>{t['ai_legend'][3:]}</h2></legend>
  <p class="help" id="ai-intro">{t['ai_intro']}</p>
{self._ai_choices(t)}
</fieldset>
<fieldset class="card" id="tour-3"><legend><h2><span class="num" aria-hidden="true">3</span>{t['contrast_legend'][3:]}</h2></legend>
{choice("checkbox", "fix_contrast", "on", "fix-contrast", t['contrast_label'], [t['contrast_help']])}
</fieldset>
<fieldset class="card" id="tour-4" aria-describedby="report-language"><legend><h2><span class="num" aria-hidden="true">4</span>{t['report_legend'][3:]}</h2></legend>
  <p class="help" id="report-language">{t['report_language']}</p>
{choice("checkbox", "review", "on", "review", t['review_label'], [t['review_help']])}
</fieldset>
<fieldset class="card" id="tour-5"><legend><h2><span class="num" aria-hidden="true">5</span>{t['protected_legend'][3:]}</h2></legend>
  <label for="password">{t['password_label']}</label>
  <p class="help" id="password-help">{t['password_help']}</p>
  <input type="password" id="password" name="password" autocomplete="off" aria-describedby="password-help">
</fieldset>
<div class="actions" id="tour-6"><button type="submit" class="big"{' disabled' if busy else ''}>{t['start']} <span aria-hidden="true">→</span></button></div>
</form>
<form method="post" action="/{self.token}/quit"><p><button type="submit" class="secondary">{t['quit']}</button></p></form>
"""
        nav = (f'<nav aria-label="{t["lang_nav"]}"><a href="/{self.token}/?lang={other}" lang="{other}">'
               f'{"Deutsch" if other == "de" else "English"}</a></nav>')
        body += tour(language, self.token, auto=not tour_seen())
        return page(language, t["title"], body, token=self.token, nav=nav)

    def _ai_choices(self, t: dict) -> str:
        """Section 2: what stays on this computer, and what is sent over the internet. Each box says
        what is set up; an option that is not set up cannot be chosen. The safe choice is preselected."""
        from pdfaccessguru.LLM.client import local_model, online_key_service
        from pdfaccessguru.utils.environment_variables import user_env_file

        model, service = local_model(), online_key_service()
        ollama_state = t["ai_ollama_found"].format(model=model) if model else t["ai_ollama_missing"]
        key_state = t["ai_key_found"].format(name=service) if service else t["ai_key_missing"].format(path=_shown_path(user_env_file()))
        return f"""  <div role="group" aria-labelledby="ai-local"><h3 class="group" id="ai-local">{t['ai_group_local']}</h3>
{choice("radio", "ai", "ollama", "ai-ollama", t['ai_ollama'], [t['ai_ollama_help'], ollama_state], checked=bool(model), disabled=not model)}
{choice("radio", "ai", "none", "ai-none", t['ai_none'], [t['ai_none_help']], checked=not model)}
  </div>
  <div role="group" aria-labelledby="ai-online"><h3 class="group" id="ai-online">{t['ai_group_online']}</h3>
{choice("radio", "ai", "cloud", "ai-cloud", t['ai_cloud'], [t['ai_cloud_help'], t['ai_key_promise'], key_state], disabled=not service)}
  </div>"""

    def job_page(self, job: Job) -> bytes:
        t = TEXT[job.language]
        if job.state == "running":
            percent = round(job.fraction * 100)
            body = f"""
<h1>{html.escape(t['working_title'].format(name=job.name))}</h1>
<p class="lead">{t['working_help']}</p>
<section class="card">
<div class="progress-head"><label for="bar">{t['progress_label']}</label><span id="percent" aria-hidden="true">{percent}%</span></div>
<progress id="bar" max="100" value="{percent}">{percent}%</progress>
<div class="status" role="status" aria-live="polite" id="status">{html.escape(job.text or '…')}</div>
<form method="post" action="/{self.token}/job/{job.job_id}/cancel"><p><button type="submit" class="secondary">{t['cancel']}</button></p></form>
<noscript><p><a href="">{t['progress_label']}: {percent}%</a></p></noscript>
</section>
"""
            script = f"""<script>
(function () {{
  var last = "";
  function poll() {{
    fetch("/{self.token}/job/{job.job_id}/status").then(function (r) {{ return r.json(); }}).then(function (s) {{
      if (s.state !== "running") {{ window.location.reload(); return; }}
      var percent = Math.round(s.fraction * 100);
      document.getElementById("bar").value = percent;
      document.getElementById("percent").textContent = percent + "%";
      if (s.text && s.text !== last) {{ document.getElementById("status").textContent = s.text; last = s.text; }}
      setTimeout(poll, 1500);
    }}).catch(function () {{ setTimeout(poll, 3000); }});
  }}
  setTimeout(poll, 1500);
}})();
</script>"""
            return page(job.language, t["working_title"].format(name=job.name), body, script, token=self.token)
        if job.state == "done":
            files = f"/{self.token}/job/{job.job_id}/file/"
            again = f'<div class="actions"><a class="button secondary" href="/{self.token}/?lang={job.language}">{t["again"]}</a></div>'
            if len(job.results) == 1:
                result = job.results[0]
                body = f"""
<h1>{html.escape(t['done_title'].format(name=job.name))}</h1>
<section class="card" aria-label="{t['summary_label']}">
{self._summary(job, result)}
</section>
<section class="card" aria-labelledby="downloads-heading"><h2 id="downloads-heading">{t['downloads']}</h2>
{self._downloads(job, result)}
</section>
<section class="card" aria-labelledby="next-heading"><h2 id="next-heading">{t['next_steps']}</h2>
{self._next_steps(job, result)}
</section>
{again}
<section class="card report" aria-labelledby="report-heading">
<h2 id="report-heading">{t['report']}</h2>
{result.report_html}
</section>
"""
                return page(job.language, t["done_title"].format(name=job.name), body, token=self.token)
            parts = [f"<h1>{html.escape(t['done_title'].format(name=job.name))}</h1>"]
            if "PDFAccessGuru.zip" in job.files:
                parts.append(f'<div class="actions"><a class="button" href="{files}PDFAccessGuru.zip" download>'
                             f'{t["download_zip"]}</a></div>')
            for number, result in enumerate(job.results, start=1):
                parts.append(f'<section class="card" aria-labelledby="file-{number}"><h2 id="file-{number}">{html.escape(result.name)}</h2>')
                if result.state == "done":
                    parts.append(self._summary(job, result))
                    parts.append(f"<h3>{t['downloads']}</h3>{self._downloads(job, result)}")
                    parts.append(f"<h3>{t['next_steps']}</h3>{self._next_steps(job, result)}")
                    parts.append(f"<details><summary>{t['show_report']}</summary>{result.report_html}</details>")
                elif result.state == "error":
                    parts.append(f'<p>{t["error_help"]}</p><div class="alert">{html.escape(result.error)}</div>')
                else:
                    parts.append(f"<p>{t['not_done']}</p>")
                parts.append("</section>")
            parts.append(again)
            return page(job.language, t["done_title"].format(name=job.name), "\n".join(parts), token=self.token)
        title = t["error_title"] if job.state == "error" else t["stopped"]
        detail = (f'<p>{t["error_help"]}</p><div class="alert" role="alert">{html.escape(job.error)}</div>'
                  if job.state == "error" else f'<div class="status" role="status">{t["stopped"]}</div>')
        body = (f"<h1>{html.escape(title)}</h1><section class=\"card\">{detail}</section>"
                f'<div class="actions"><a class="button secondary" href="/{self.token}/?lang={job.language}">{t["again"]}</a></div>')
        return page(job.language, title, body, token=self.token)

    def _summary(self, job: Job, result: Result) -> str:
        """Pass or not, in words and with a mark (never by colour alone), and the main numbers."""
        t = TEXT[job.language]
        badge = (f'<p class="badge ok"><span class="mark" aria-hidden="true">✓</span>{t["badge_ok"]}</p>' if result.passes
                 else f'<p class="badge warn"><span class="mark" aria-hidden="true">!</span>{t["badge_warn"]}</p>')
        numbers = ((t["n_fixed"], result.fixed), (t["n_open"], result.still_open), (t["n_check"], result.to_check))
        cells = "".join(f"<div><dt>{label}</dt><dd>{value}</dd></div>" for label, value in numbers)
        return f'{badge}<dl class="numbers">{cells}</dl>'

    def _next_steps(self, job: Job, result: Result) -> str:
        t = TEXT[job.language]
        number = job.results.index(result) + 1
        base = f"/{self.token}/job/{job.job_id}"
        return f"""<ul class="links">
  <li><a href="{base}/check/{number}">{t['check_link']}<span class="note">{t['check_note']}</span></a></li>
  <li><a href="{base}/preview/{number}">{t['preview_link']}<span class="note">{t['preview_note']}</span></a></li>
</ul>"""

    def _downloads(self, job: Job, result: Result) -> str:
        t = TEXT[job.language]
        files = f"/{self.token}/job/{job.job_id}/file/"
        pdf = result.files["pdf"]
        size_bytes = job.files[pdf].stat().st_size
        size = f"{size_bytes / 1e6:.1f} MB" if size_bytes >= 1e6 else f"{max(1, round(size_bytes / 1e3))} KB"
        name = pdf.split("/", 1)[1]
        return f"""<ul class="links">
  <li><a href="{files}{quote(pdf)}" download>{t['download_pdf_short']}<span class="note">{html.escape(name)}, {size}</span></a></li>
  <li><a href="{files}{quote(result.files['report_pdf'])}" download>{t['download_report_pdf']}<span class="note">{t['report_pdf_note']}</span></a></li>
  <li><a href="{files}{quote(result.files['report_md'])}" download>{t['download_report_md']}<span class="note">{t['report_md_note']}</span></a></li>
</ul>"""


    # --- checking the texts and the screen reader preview (Phase 7b) -----------------------------

    def _fixed(self, job: Job, result: Result) -> Path:
        return job.files[result.files["pdf"]]

    def check_page(self, job: Job, number: int, message: str = "", alert: bool = False) -> bytes:
        from pdfaccessguru.webapp.review import GROUPS, collect, version

        t = TEXT[job.language]
        result = job.results[number - 1]
        fixed = self._fixed(job, result)
        entries = collect(fixed, result.source)
        back = f"/{self.token}/job/{job.job_id}"
        parts = [f"<h1>{html.escape(t['check_title'].format(name=result.name))}</h1>",
                 f"<p class=\"lead\">{t['check_intro']}</p>"]
        if message:
            role = "alert" if alert else "status"
            parts.append(f'<div class="{"alert" if alert else "status"}" role="{role}">{html.escape(message)}</div>')
        parts.append(f'<form method="post" action="{back}/check/{number}">'
                     f'<input type="hidden" name="version" value="{version(fixed)}">')
        for group in GROUPS:
            items = [entry for entry in entries if entry.group == group]
            if not items:
                continue
            done = f" – {t['checked']}" if group in result.checked else ""
            parts.append(f'<fieldset class="card"><legend><h2>{t["group_" + group].format(n=len(items))}{done}</h2></legend>')
            for entry in items:
                label = t["label_" + entry.key] if entry.key in ("title", "lang") else \
                    t["label_" + group].format(page=entry.page or "?")
                help_id = f"help-{entry.key}"
                help_text = entry.context or (t["lang_help"] if entry.key == "lang" else "")
                described = f' aria-describedby="{help_id}"' if help_text else ""
                parts.append('<div class="entry">')
                parts.append(f'<label for="{entry.key}">{html.escape(label)}</label>')
                if help_text:
                    parts.append(f'<p class="help" id="{help_id}">{html.escape(help_text)}</p>')
                if entry.has_picture:
                    parts.append(f'<img src="{back}/picture/{number}/{entry.key}.png" alt="" loading="lazy">')
                if group == "document":
                    parts.append(f'<input type="text" id="{entry.key}" name="{entry.key}" value="{html.escape(entry.text)}"{described}>')
                else:
                    parts.append(f'<textarea id="{entry.key}" name="{entry.key}" rows="2"{described}>{html.escape(entry.text)}</textarea>')
                parts.append("</div>")
            if group != "document":
                parts.append(f'<p><button type="submit" name="accept" value="{group}" class="secondary">'
                             f'{t["accept_" + group]}</button></p>')
            parts.append("</fieldset>")
        parts.append(self._hidden_section(job, number, fixed))
        if len(entries) <= 2:
            parts.append(f"<p>{t['nothing_written']}</p>")
        parts.append(f'<div class="actions"><button type="submit" class="big" name="accept" value="">{t["save"]}</button></div></form>')
        parts.append(f'<p><a href="{back}">{t["back"]}</a></p>')
        return page(job.language, t["check_title"].format(name=result.name), "\n".join(parts), token=self.token)

    def _hidden_section(self, job: Job, number: int, fixed: Path) -> str:
        """What the tool hid as decoration: pictures can be shown again with a description; hidden
        text (page headers, footers, numbers) is listed so it can be checked."""
        from pdfaccessguru.webapp.review import hidden_pictures, hidden_text

        t = TEXT[job.language]
        pictures, lines = hidden_pictures(fixed), hidden_text(fixed)
        back = f"/{self.token}/job/{job.job_id}"
        parts = [f'<fieldset class="card"><legend><h2>{t["hidden_title"]}</h2></legend>',
                 f'<p class="help">{t["hidden_intro"]}</p>']
        if not pictures and not lines:
            parts.append(f"<p>{t['hidden_none']}</p>")
        for picture in pictures:
            pages = ", ".join(str(n) for n in picture.pages[:12]) + (" …" if len(picture.pages) > 12 else "")
            parts.append('<div class="entry">')
            parts.append(f'<div class="choice"><input type="checkbox" id="show-{picture.key}" name="show-{picture.key}" '
                         f'aria-describedby="where-{picture.key}"><label for="show-{picture.key}">'
                         f'{t["hidden_show"]}</label></div>')
            parts.append(f'<p class="help" id="where-{picture.key}">{html.escape(t["hidden_where"].format(pages=pages))}</p>')
            parts.append(f'<img src="{back}/picture/{number}/{picture.key}.png" alt="" loading="lazy">')
            parts.append(f'<label for="describe-{picture.key}">{t["hidden_describe"]}</label>')
            parts.append(f'<textarea id="describe-{picture.key}" name="describe-{picture.key}" rows="2"></textarea>')
            parts.append("</div>")
        if lines:
            parts.append(f"<h3>{t['hidden_text']}</h3><ul>")
            for text, count in lines:
                parts.append(f"<li>“{html.escape(text)}” – {html.escape(t['hidden_pages'].format(n=count))}</li>")
            parts.append("</ul>")
        parts.append("</fieldset>")
        return "\n".join(parts)

    def save_checks(self, job: Job, number: int, fields: dict[str, str]) -> bytes:
        from pdfaccessguru.webapp.review import EditError, apply, collect, version

        t = TEXT[job.language]
        result = job.results[number - 1]
        fixed = self._fixed(job, result)
        if fields.get("version") != version(fixed):
            return self.check_page(job, number, t["changed_meanwhile"], alert=True)
        before = {entry.key: entry for entry in collect(fixed, result.source)}
        changes = {key: value for key, value in fields.items()
                   if key not in ("version", "accept") and not key.startswith(("show-", "describe-"))}
        show = {key[len("show-"):]: fields.get("describe-" + key[len("show-"):], "")
                for key, value in fields.items() if key.startswith("show-") and value}
        try:
            changed = apply(fixed, changes, show)
        except EditError as error:
            reason = {"empty": "empty_text", "language": "bad_language", "empty_picture": "empty_picture"}.get(
                str(error), "cannot_show")
            return self.check_page(job, number, t[reason], alert=True)
        if fields.get("accept"):
            result.checked.add(fields["accept"])
        result.preview = ""
        if result.report is not None and _remember_review(result.report, before, changes, show, fields.get("accept", "")):
            self._write_report(job, number, result)
        if "PDFAccessGuru.zip" in job.files:
            self._zip_all(job)
        return self.check_page(job, number, t["saved"])

    def preview_page(self, job: Job, number: int) -> bytes:
        from pdfaccessguru.webapp.preview import preview_html

        t = TEXT[job.language]
        result = job.results[number - 1]
        if not result.preview:
            result.preview = preview_html(self._fixed(job, result), job.language)
        body = (f"<h1>{html.escape(t['preview_title'].format(name=result.name))}</h1><p class=\"lead\">{t['preview_intro']}</p>"
                f"<section class=\"card\">{result.preview}</section>"
                f"<p><a href=\"/{self.token}/job/{job.job_id}\">{t['back']}</a></p>")
        return page(job.language, t["preview_title"].format(name=result.name), body, token=self.token)


def _shown_path(path: Path) -> str:
    """A path as shown on a page: the home folder as ~ on Mac and Linux (shorter, and the user name
    does not end up in screenshots people share)."""
    home = str(Path.home())
    text = str(path)
    if os.name != "nt" and text.startswith(home + os.sep):
        return "~" + text[len(home):]
    return text


def tour_seen() -> bool:
    """True once the guided tour was shown (kept in the app's settings file, not in the browser:
    the app opens at a new address every time, so the browser would forget it)."""
    from pdfaccessguru.updates import settings_file

    try:
        return bool(json.loads(settings_file().read_text(encoding="utf-8")).get("tour_seen"))
    except (OSError, ValueError):
        return False


def mark_tour_seen() -> None:
    from pdfaccessguru.updates import settings_file

    path = settings_file()
    try:
        settings = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        settings = {}
    if not isinstance(settings, dict):
        settings = {}
    settings["tour_seen"] = True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=1), encoding="utf-8")
    except OSError:                                     # then it shows again next time; nothing breaks
        pass


def _remember_review(report: dict, before: dict, changes: dict[str, str], show: dict[str, str], accept: str) -> bool:
    """
    Add what the user changed or reviewed on the review page to report["user_review"], so the
    report can say it (Phase 12c). `before` are the review page's entries before saving. A text
    changed twice keeps the tool's text as "old"; changed back to the tool's text, it is dropped.
    Returns True if anything was added.
    """
    from pdfaccessguru.reporting.review_list import APP_GROUPS

    review = report.setdefault("user_review", {"changes": [], "reviewed": [], "shown": 0})
    added = False
    for key, text in changes.items():
        entry = before.get(key)
        new = " ".join(text.split())
        if entry is None or new == " ".join(entry.text.split()):
            continue
        group = APP_GROUPS[entry.key] if entry.key in ("title", "lang") else APP_GROUPS.get(entry.group, "other")
        earlier = next((change for change in review["changes"]
                        if change["group"] == group and change["new"] == " ".join(entry.text.split())), None)
        if earlier is None:
            review["changes"].append({"group": group, "page": entry.page, "old": entry.text, "new": new})
        elif new == " ".join(earlier["old"].split()):
            review["changes"].remove(earlier)
        else:
            earlier["new"] = new
        added = True
    shown = sum(1 for description in show.values() if description.strip())
    if shown:
        review["shown"] += shown
        added = True
    if accept in APP_GROUPS and APP_GROUPS[accept] not in review["reviewed"]:
        review["reviewed"].append(APP_GROUPS[accept])
        added = True
    return added


def _handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args) -> None:            # no request logging in the terminal
            pass

        def _send(self, status: int, body: bytes, content_type: str = "text/html; charset=utf-8",
                  extra: dict[str, str] | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; "
                                                        "script-src 'unsafe-inline'; img-src 'self'")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def _redirect(self, location: str) -> None:
            self._send(303, b"", extra={"Location": location})

        def _route(self) -> list[str] | None:
            app.last_use = time.time()
            parts = urlparse(self.path).path.strip("/").split("/")
            if not parts or not secrets.compare_digest(parts[0], app.token):
                self._send(403, b"Forbidden", "text/plain")
                return None
            return parts[1:]

        def _language(self) -> str:
            query = parse_qs(urlparse(self.path).query)
            if "lang" in query:
                return "de" if query["lang"][0] == "de" else "en"
            accepted = self.headers.get("Accept-Language", "")
            return "de" if accepted.lower().startswith("de") else "en"

        def do_GET(self) -> None:
            parts = self._route()
            if parts is None:
                return
            if parts in ([], [""]):
                self._send(200, app.form(self._language()))
                return
            if len(parts) == 2 and parts[0] == "static":
                kinds = {".woff2": "font/woff2", ".svg": "image/svg+xml", ".txt": "text/plain; charset=utf-8"}
                path = STATIC / parts[1]
                if parts[1] in STATIC_FILES and path.suffix in kinds:
                    self._send(200, path.read_bytes(), kinds[path.suffix])
                    return
            if len(parts) >= 2 and parts[0] == "job" and parts[1] in app.jobs:
                job = app.jobs[parts[1]]
                if len(parts) == 2:
                    self._send(200, app.job_page(job))
                    return
                number = int(parts[3]) if len(parts) >= 4 and parts[3].isdigit() else 0
                ready = job.state == "done" and 1 <= number <= len(job.results) and job.results[number - 1].state == "done"
                if len(parts) == 4 and parts[2] == "check" and ready:
                    self._send(200, app.check_page(job, number))
                    return
                if len(parts) == 4 and parts[2] == "preview" and ready:
                    self._send(200, app.preview_page(job, number))
                    return
                if len(parts) == 5 and parts[2] == "picture" and ready and parts[4].endswith(".png"):
                    from pdfaccessguru.webapp.review import hidden_picture_png, picture
                    key = parts[4][:-4]
                    fixed = app._fixed(job, job.results[number - 1])
                    data = hidden_picture_png(fixed, key) if key.startswith("img-") else picture(fixed, key)
                    if data:
                        self._send(200, data, "image/png")
                        return
                if parts[2:] == ["status"]:
                    data = {"state": job.state, "text": job.text, "fraction": job.fraction}
                    self._send(200, json.dumps(data).encode(), "application/json")
                    return
                if len(parts) >= 4 and parts[2] == "file":
                    relative = "/".join(parts[3:])
                    from urllib.parse import unquote
                    path = job.files.get(unquote(relative))
                    if path is not None and path.is_file():
                        kind = {"pdf": "application/pdf", "md": "text/markdown; charset=utf-8", "png": "image/png",
                                "zip": "application/zip"}.get(path.suffix.lstrip("."), "application/octet-stream")
                        disposition = {} if kind == "image/png" else {
                            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(path.name)}"}
                        self._send(200, path.read_bytes(), kind, disposition)
                        return
            self._send(404, b"Not found", "text/plain")

        def do_POST(self) -> None:
            parts = self._route()
            if parts is None:
                return
            if parts == ["quit"]:
                self._send(200, page("en", "PDFAccessGuru", f"<h1>PDFAccessGuru</h1><p>{TEXT['en']['quit_done']}</p>"
                                     f"<p lang=\"de\">{TEXT['de']['quit_done']}</p>", token=app.token))
                threading.Thread(target=app.server.shutdown, daemon=True).start()
                return
            if len(parts) == 3 and parts[0] == "job" and parts[2] == "cancel" and parts[1] in app.jobs:
                app.jobs[parts[1]].cancel.set()
                self._redirect(f"/{app.token}/job/{parts[1]}")
                return
            if parts == ["start"]:
                self._start()
                return
            if (len(parts) == 4 and parts[0] == "job" and parts[1] in app.jobs and parts[2] == "check"
                    and parts[3].isdigit()):
                job = app.jobs[parts[1]]
                number = int(parts[3])
                if job.state == "done" and 1 <= number <= len(job.results) and job.results[number - 1].state == "done":
                    length = int(self.headers.get("Content-Length", 0))
                    fields = {key: values[0] for key, values in
                              parse_qs(self.rfile.read(length).decode("utf-8", "replace"), keep_blank_values=True).items()}
                    self._send(200, app.save_checks(job, number, fields))
                    return
            if parts == ["tour-seen"]:
                mark_tour_seen()
                self._send(204, b"")
                return
            if parts == ["install"]:
                app.install_tools()
                self._redirect(f"/{app.token}/?lang={self._language()}")
                return
            if parts == ["update"]:
                language = self._language()
                from pdfaccessguru.updates import start_update_after_exit
                if app.running_job() is None and start_update_after_exit(reopen_app=True):
                    self._send(200, page(language, "PDFAccessGuru",
                                         f"<h1>PDFAccessGuru</h1><p role=\"status\">{TEXT[language]['updating']}</p>",
                                         token=app.token))
                    threading.Thread(target=app.server.shutdown, daemon=True).start()
                else:
                    self._send(200, app.form(language, TEXT[language]["update_manual"]))
                return
            self._send(404, b"Not found", "text/plain")

        def _start(self) -> None:
            length = int(self.headers.get("Content-Length", 0))
            if length > MAX_UPLOAD:
                self._send(413, b"File too large", "text/plain")
                return
            raw = self.rfile.read(length)
            message = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
                b"Content-Type: " + self.headers.get("Content-Type", "").encode() + b"\r\n\r\n" + raw)
            options: dict[str, str] = {}
            uploads: list[tuple[str, bytes]] = []
            for part in message.iter_parts():
                name = part.get_param("name", header="content-disposition")
                if name == "file":
                    data = part.get_payload(decode=True) or b""
                    if data:
                        uploads.append((part.get_filename() or "", data))
                elif name:
                    options[name] = (part.get_payload(decode=True) or b"").decode("utf-8", "replace")
            language = "de" if options.get("language_ui") == "de" else "en"
            if not uploads:
                self._send(400, app.form(language, TEXT[language]["no_file"]))
                return
            not_pdf = [Path(name).name for name, data in uploads if not data.startswith(b"%PDF")]
            if not_pdf:
                self._send(400, app.form(language, TEXT[language]["not_pdf"].format(names=", ".join(not_pdf))))
                return
            with app.lock:
                if app.running_job() is not None:
                    self._send(409, app.form(language, TEXT[language]["busy"]))
                    return
                job = app.start_job(uploads, options)
            self._redirect(f"/{app.token}/job/{job.job_id}")

    return Handler


def serve(open_browser: bool = True, port: int = 0) -> None:
    """Start the app and (by default) open it in the browser. Returns when the app is closed."""
    from pdfaccessguru.pipeline.reporting.console import set_console_output

    set_console_output(False)
    app = App()
    app.server = ThreadingHTTPServer(("127.0.0.1", port), _handler(app))
    url = f"http://127.0.0.1:{app.server.server_address[1]}/{app.token}/"
    print(f"PDFAccessGuru is open in your browser. If not, open this address: {url}", flush=True)
    print("To close the app, use the button 'Close the app' on the page, or press Ctrl+C here.", flush=True)

    def stop_when_idle() -> None:
        while True:
            time.sleep(60)
            if time.time() - app.last_use > IDLE_SHUTDOWN and app.running_job() is None:
                app.server.shutdown()
                return

    threading.Thread(target=stop_when_idle, daemon=True).start()
    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        app.server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.server.server_close()
        shutil.rmtree(app.work, ignore_errors=True)
