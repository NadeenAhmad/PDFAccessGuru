"""
Starts the app: the accessible browser app (webapp/), which works with screen readers and the
keyboard. It runs only on this computer and opens in the web browser.
"""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))


def main(open_browser: bool = True) -> None:
    from pdfaccessguru.webapp.server import serve

    serve(open_browser=open_browser)


if __name__ == "__main__":
    main()
