"""
Starts the app: the accessible browser app (webapp/), which works with screen readers and the
keyboard. It runs only on this computer and opens in the web browser.
"""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))


def main(open_browser: bool = True) -> None:
    from pdfaccessguru.shortcuts import refresh_after_update
    from pdfaccessguru.webapp.server import open_running_app, serve

    refresh_after_update()                    # after an update: newest icon and program in the shortcut
    if open_running_app(open_browser):        # already running: show it again instead of a second app
        return

    serve(open_browser=open_browser)


if __name__ == "__main__":
    main()
