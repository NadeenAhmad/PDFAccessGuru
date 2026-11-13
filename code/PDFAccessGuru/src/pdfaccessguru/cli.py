"""
Command line for PDFAccessGuru.

    pdfaccessguru                     open the app
    pdfaccessguru fix FILE.pdf        fix a file and write a report next to it
    pdfaccessguru fix A.pdf B.pdf     fix several files (or a whole folder) one after the other
    pdfaccessguru check FILE.pdf      only check a file, change nothing
    pdfaccessguru doctor              check that everything needed is installed
    pdfaccessguru update              update to the newest version
    pdfaccessguru uninstall           remove PDFAccessGuru from this computer
    pdfaccessguru --version

Messages are short and plain, because many users are not technical.
Exit codes: 0 = the file passes the automatic check, 1 = problems remain, 2 = the tool could not run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from pdfaccessguru import __version__

EXIT_OK, EXIT_PROBLEMS, EXIT_ERROR = 0, 1, 2



def _say(message: str) -> None:
    print(message, flush=True)


def _fail(message: str) -> int:
    print(f"Error: {message}", file=sys.stderr, flush=True)
    return EXIT_ERROR


def _progress_printer():
    """Print each new step once ("Fixing fonts and characters ..."), not every update."""
    last = {"text": None}

    def show(text: str, fraction: float) -> None:
        if text != last["text"] and fraction < 1.0:   # the summary follows the last step
            last["text"] = text
            _say(f"{text} ...")

    return show


def _ensure_helper_programs() -> bool:
    """Install Java and veraPDF on first use. Returns False (after telling the user) if that fails."""
    from pdfaccessguru.tool_installer import ToolInstallError, ensure_tools, tools_missing

    if not tools_missing():
        return True
    _say("PDFAccessGuru needs two free helper programs and some free fonts (Java, veraPDF and the Liberation fonts, about 77 MB).")
    _say("They are downloaded once into your user folder. No admin rights are needed.")
    try:
        ensure_tools(progress=_say)
    except ToolInstallError as error:
        _fail(str(error))
        return False
    _say("")
    return True


def _input_pdf(path_text: str) -> Path | None:
    path = Path(path_text).expanduser()
    if not path.is_file():
        _fail(f"The file '{path}' was not found.")
        return None
    if path.suffix.lower() != ".pdf":
        _fail(f"'{path.name}' is not a PDF file.")
        return None
    return path.resolve()


def _pdfs_to_fix(paths: list[str]) -> list[Path] | None:
    """The PDF files named on the command line; a folder means every PDF directly inside it
    (except files this tool made, *_accessible.pdf and *_report.pdf)."""
    found: list[Path] = []
    for path_text in paths:
        path = Path(path_text).expanduser()
        if path.is_dir():
            inside = sorted(p for p in path.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"
                            and not p.stem.endswith(("_accessible", "_report")))
            if not inside:
                _fail(f"The folder '{path}' contains no PDF files.")
                return None
            found += [p.resolve() for p in inside]
            continue
        source = _input_pdf(path_text)
        if source is None:
            return None
        found.append(source)
    return list(dict.fromkeys(found))


def _cmd_fix(args: argparse.Namespace) -> int:
    sources = _pdfs_to_fix(args.file)
    if not sources or not _ensure_helper_programs():
        return EXIT_ERROR
    if args.output and len(sources) > 1:
        return _fail("-o can only be used with one file. With several files, each new file is saved next to its original.")
    from pdfaccessguru.pipeline.reporting.console import set_console_output

    if getattr(args, "ai", None):
        os.environ["PDFACCESSGURU_AI"] = args.ai
    if getattr(args, "descriptions", None):
        os.environ["PDFACCESSGURU_DESCRIPTIONS"] = args.descriptions
    if getattr(args, "local_only", False):
        os.environ["PDFACCESSGURU_PRIVACY"] = "local"
    results = []
    for number, source in enumerate(sources, start=1):
        if len(sources) > 1:
            _say(f"\n[{number}/{len(sources)}]")
        set_console_output(args.verbose)
        try:
            results.append((source, _fix_one(source, args)))
        finally:
            set_console_output(True)
    if len(sources) > 1:
        _say("\nSummary:")
        for source, code in results:
            word = {EXIT_OK: "passes the check", EXIT_PROBLEMS: "problems still open", EXIT_ERROR: "could not be processed"}
            _say(f"  {source.name}: {word.get(code, '?')}")
    _update_hint()
    codes = [code for _, code in results]
    return EXIT_ERROR if EXIT_ERROR in codes else EXIT_PROBLEMS if EXIT_PROBLEMS in codes else EXIT_OK


def _fix_one(source: Path, args: argparse.Namespace) -> int:
    from pdfaccessguru.pipeline.pipeline import run_pipeline
    from pdfaccessguru.reporting import (
        build_customer_report_images,
        build_customer_report_markdown,
        build_customer_report_pdf,
        build_report_metrics,
    )
    from pdfaccessguru.reporting.report_language import language_name, report_language

    output = Path(args.output).expanduser().resolve() if args.output else source.with_name(f"{source.stem}_accessible.pdf")
    if output == source:
        return _fail("The new file must not replace the original. Choose another name with -o.")
    if output.exists() and not args.overwrite:
        return _fail(f"'{output.name}' already exists. Use --overwrite to replace it, or choose another name with -o.")
    owner_password = None
    if getattr(args, "ask_owner_password", False):
        import getpass
        owner_password = getpass.getpass(f"Owner password of {source.name} (not shown, not stored; Enter to skip): ") or None
    _say(f"PDFAccessGuru {__version__}: {source.name}")
    try:
        report = run_pipeline(str(source), str(output), progress_callback=_progress_printer(),
                              owner_password=owner_password, fix_contrast=getattr(args, "fix_contrast", False))
    except Exception as error:  # the pipeline reports details in the log; the user gets one clear line
        return _fail(f"The file could not be processed: {error}")

    include_review = include_pictures = args.review_list       # the review list always shows the pictures
    language = args.language if args.language and args.language != "auto" else report_language(output)
    report_base = output.with_name(f"{output.stem}_report")
    report_base.with_suffix(".md").write_text(
        build_customer_report_markdown(report, include_review, include_pictures, language), encoding="utf-8"
    )
    if include_pictures:
        for relative_path, data in build_customer_report_images(report).items():
            image_path = report_base.parent / relative_path
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(data)
    if args.pdf_report:
        report_base.with_suffix(".pdf").write_bytes(build_customer_report_pdf(report, include_review, include_pictures, language))
    if args.json:
        report_base.with_suffix(".json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")

    metrics = build_report_metrics(report)
    _say("")
    _say(f"Passes the automatic check: {'Yes' if metrics.passes_verapdf else 'No'}")
    _say(f"Problems fixed: {metrics.corrected_count}. Still open: {metrics.remaining_count}.")
    if metrics.review_items:
        _say(f"Texts the tool wrote for you to review: {len(metrics.review_items)}"
             + ("" if include_review else " (add --review-list to list them in the report)"))
    _say(f"New file: {output}")
    _say(f"Report:   {report_base.with_suffix('.md')} (in {language_name(language)}, the language of the PDF)"
         if not args.language or args.language == "auto" else f"Report:   {report_base.with_suffix('.md')}")
    return EXIT_OK if metrics.passes_verapdf else EXIT_PROBLEMS


def _cmd_check(args: argparse.Namespace) -> int:
    import pikepdf

    from pdfaccessguru.pipeline.PDFAccessGuruDetect.verapdf.verapdf_runner import run_verapdf
    from pdfaccessguru.pipeline.text_tagging import measure_text_tagging

    source = _input_pdf(args.file)
    if source is None or not _ensure_helper_programs():
        return EXIT_ERROR
    try:
        violations = run_verapdf(str(source))
        with pikepdf.open(source) as pdf:
            tagging = measure_text_tagging(pdf)
    except Exception as error:
        return _fail(f"The file could not be checked: {error}")

    kinds = len({violation.rule_id for violation in violations})
    _say(f"{source.name}")
    _say(f"Passes the automatic check: {'Yes' if not violations else 'No'}")
    if violations:
        _say(f"Problems found: {len(violations)} (of {kinds} different kinds)")
    if tagging["total"]:
        _say(f"Text that a screen reader can read: {tagging['tagged_share'] * 100:.0f}%")
    _say("Nothing was changed. Use 'pdfaccessguru fix' to fix the file.")
    _update_hint()
    return EXIT_OK if not violations else EXIT_PROBLEMS


def _cmd_doctor(args: argparse.Namespace) -> int:
    from pdfaccessguru.setup_check import run_setup_checks

    if args.install:
        from pdfaccessguru.tool_installer import ToolInstallError, ensure_tools

        _say("Installing the helper programs (Java and veraPDF) into your user folder ...")
        try:
            ensure_tools(progress=_say, force=True)
        except ToolInstallError as error:
            return _fail(str(error))
        _say("")

    all_ok = True
    for check in run_setup_checks():
        status = "OK     " if check.ok else ("NOTE   " if check.optional else "MISSING")
        _say(f"{status}  {check.name}: {check.detail}")
        if not check.ok:
            all_ok = all_ok and check.optional
            if check.how_to_fix:
                _say(f"         What to do: {check.how_to_fix}")
    _say("")
    _say("Everything needed is installed." if all_ok else "Some required parts are missing (see 'What to do' above).")
    return EXIT_OK if all_ok else EXIT_ERROR


def _cmd_update(_args: argparse.Namespace) -> int:
    import platform

    from pdfaccessguru.updates import check_for_update, manual_update_hint, run_update_now, start_update_after_exit

    info = check_for_update(force=True, timeout=10)
    if info is None:
        _say(f"You have the newest version ({__version__}), or the update server could not be reached.")
        return EXIT_OK
    _say(f"Updating PDFAccessGuru from {info.current} to {info.latest} ...")
    if platform.system() == "Windows":
        if start_update_after_exit(reopen_app=False, expected=info.latest):
            _say("The update starts in a few seconds, after this window has finished. Then run your command again.")
            return EXIT_OK
    else:
        result = run_update_now(info.latest, say=_say)
        if result == "done":
            _say("Done. PDFAccessGuru is up to date.")
            return EXIT_OK
        if result == "not_ready":
            _say("The new version is not ready on the server yet. Please try again in a few minutes: pdfaccessguru update")
            return EXIT_ERROR
    _say(manual_update_hint())
    return EXIT_ERROR


def _update_hint() -> None:
    """One line after a command if a newer version exists (checked at most once a day)."""
    from pdfaccessguru.updates import check_for_update

    info = check_for_update()
    if info is not None:
        _say(f"\nA new version of PDFAccessGuru ({info.latest}) is available. Run 'pdfaccessguru update' to get it.")


def _cmd_shortcut(args: argparse.Namespace) -> int:
    from pdfaccessguru.shortcuts import create_shortcut, remove_shortcut

    if args.remove:
        remove_shortcut()
        _say("The PDFAccessGuru shortcut was removed.")
        return EXIT_OK
    try:
        target = create_shortcut()
    except Exception as error:
        return _fail(f"The shortcut could not be created: {error}")
    _say(f"Shortcut created: {target}")
    return EXIT_OK


def _cmd_uninstall(args: argparse.Namespace) -> int:
    import shutil

    from platformdirs import user_cache_dir, user_config_dir

    from pdfaccessguru.external_tools import tools_dir
    from pdfaccessguru.shortcuts import remove_shortcut
    from pdfaccessguru.updates import start_after_exit, uninstall_command

    if not args.yes:
        answer = input("Remove PDFAccessGuru, its helper programs and its settings from this computer? [y/N] ")
        if answer.strip().lower() not in ("y", "yes", "j", "ja"):
            _say("Nothing was removed.")
            return EXIT_OK
    remove_shortcut()
    shutil.rmtree(tools_dir(), ignore_errors=True)
    shutil.rmtree(user_cache_dir("pdfaccessguru"), ignore_errors=True)
    if not args.keep_settings:
        shutil.rmtree(user_config_dir("pdfaccessguru"), ignore_errors=True)
    command = uninstall_command()
    if command is None:
        _say("The shortcut, helper programs and settings were removed. Remove the program itself the way you installed it.")
        return EXIT_OK
    start_after_exit(command)
    _say("PDFAccessGuru is being removed. This finishes a few seconds after this window is done.")
    _say("Your PDF files and reports are not touched.")
    return EXIT_OK


def _cmd_app(args: argparse.Namespace) -> int:
    from pdfaccessguru.app import main as app_main

    app_main(open_browser=not getattr(args, "no_browser", False))
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdfaccessguru",
        description="Finds and fixes accessibility problems in PDF files. Run without a command to open the app.",
    )
    parser.add_argument("--version", action="version", version=f"PDFAccessGuru {__version__}")
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")

    fix = commands.add_parser("fix", help="fix PDF files and write a report next to each")
    fix.add_argument("file", nargs="+", help="the PDF files to fix, or a folder (the originals are not changed)")
    fix.add_argument("-o", "--output", help="name of the new file (default: NAME_accessible.pdf)")
    fix.add_argument("--overwrite", action="store_true", help="replace the new file if it already exists")
    fix.add_argument("--review-list", action="store_true", help="add a review list to the report: everything the tool decided by itself")
    fix.add_argument("--pdf-report", action="store_true", help="also write the report as a PDF")
    fix.add_argument("--fix-contrast", action="store_true",
                     help="make text with too little colour contrast darker or lighter (changes text colours; "
                          "leave it off for templates whose colours must not change)")
    fix.add_argument("--language", default="auto",
                     help="language of the report; by default the language of the PDF. English and German are "
                          "built in; other languages (e.g. ar, fr) are translated by the AI")
    fix.add_argument("--json", action="store_true", help="also write the full technical data as JSON")
    fix.add_argument("--verbose", action="store_true", help="show every technical message while working")
    fix.add_argument("--ai", choices=["auto", "ollama", "openai", "openrouter", "none"],
                     help="which AI writes texts like picture descriptions (default: auto = a key if set, "
                          "else Ollama on this computer, else none)")
    fix.add_argument("--descriptions", choices=["brief", "standard", "detailed"],
                     help="how detailed picture descriptions written by an AI are: brief (one sentence), standard "
                          "(default: short for simple pictures, fuller for charts and diagrams) or detailed")
    fix.add_argument("--ask-owner-password", action="store_true",
                     help="for protected PDFs: ask for the owner password, so that the tool can let "
                          "screen readers read the file (the password is not stored)")
    fix.add_argument("--local-only", action="store_true",
                     help="privacy: never send document content to the internet (only Ollama on this computer)")
    fix.set_defaults(handler=_cmd_fix)

    check = commands.add_parser("check", help="only check a PDF file, change nothing")
    check.add_argument("file", help="the PDF file to check")
    check.set_defaults(handler=_cmd_check)

    doctor = commands.add_parser("doctor", help="check that everything needed is installed")
    doctor.add_argument("--install", action="store_true", help="download and install the helper programs (Java, veraPDF)")
    doctor.set_defaults(handler=_cmd_doctor)

    update = commands.add_parser("update", help="update PDFAccessGuru to the newest version")
    update.set_defaults(handler=_cmd_update)

    shortcut = commands.add_parser("shortcut", help="add PDFAccessGuru to the Start menu / Applications / app menu")
    shortcut.add_argument("--remove", action="store_true", help="remove the shortcut again")
    shortcut.set_defaults(handler=_cmd_shortcut)

    uninstall = commands.add_parser("uninstall", help="remove PDFAccessGuru from this computer")
    uninstall.add_argument("--yes", action="store_true", help="do not ask for confirmation")
    uninstall.add_argument("--keep-settings", action="store_true", help="keep settings such as API keys")
    uninstall.set_defaults(handler=_cmd_uninstall)

    app = commands.add_parser("app", help="open the app in your browser (same as running without a command)")
    app.add_argument("--no-browser", action="store_true", help="only print the address, do not open the browser")
    app.set_defaults(handler=_cmd_app)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    handler = getattr(args, "handler", _cmd_app)
    sys.exit(handler(args))


if __name__ == "__main__":
    main()
