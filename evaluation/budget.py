"""
Keeps the online AI spending of the evaluation below the agreed limit: EUR 10 in total.

Counts only OUR requests: every paid request is looked up at OpenRouter (its exact price) and written
to the cost log. The key itself is also used for other things, so its total is only a cross-check.
Never prints, logs or stores the key.

    python evaluation/budget.py          # spent so far, and a cross-check of the key's total
"""

from __future__ import annotations

import csv
import datetime
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from paths import COST_LOG, WORK

LIMIT_EUR = 10.00
USD_PER_EUR = 1.1193            # ECB reference rate, 9 Nov 2026
STOP_USD = 9.00                 # stop line, about EUR 8: OpenRouter's totals arrive with a delay
_FIELDS = ["time", "step", "model", "request_id", "cost_usd", "note"]
_SETTINGS = [Path.home() / "Library" / "Application Support" / "pdfaccessguru" / ".env",   # PDFAccessGuru's settings
             Path.home() / ".config" / "pdfaccessguru" / ".env",
             Path(os.environ.get("LOCALAPPDATA", Path.home())) / "pdfaccessguru" / "pdfaccessguru" / ".env"]


class BudgetExceeded(RuntimeError):
    pass


def _key() -> str:
    """The OpenRouter key from the environment, or else from PDFAccessGuru's settings file."""
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    for settings in _SETTINGS:
        if settings.is_file():
            for line in settings.read_text(encoding="utf-8").splitlines():
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _get(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {_key()}", "User-Agent": "pdfaccessguru-eval"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def request_cost(request_id: str, attempts: int = 15) -> float | None:
    """The exact price of one request in USD, as OpenRouter bills it (None if it never shows up)."""
    for attempt in range(attempts):
        try:
            data = _get(f"https://openrouter.ai/api/v1/generation?id={request_id}")["data"]
            return float(data.get("total_cost") or 0.0)
        except urllib.error.HTTPError as error:
            if error.code not in (404, 429, 500, 502, 503, 504):
                raise
            time.sleep(2 + attempt)                          # not booked yet, or the service is busy
        except (OSError, ValueError, KeyError):              # timeout, lost connection, odd answer: ask again
            time.sleep(2 + attempt)
    return None                                              # record() then counts USD 0.01, on the safe side


def _append(rows: list[dict]) -> None:
    new = not COST_LOG.exists()
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with COST_LOG.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_FIELDS)
        if new:
            writer.writeheader()
        writer.writerows(rows)


def record(step: str, requests: list[dict]) -> float:
    """Looks up and logs each request ({'id', 'model'}); returns their total in USD."""
    now = datetime.datetime.now().isoformat(timespec="seconds")
    rows, total = [], 0.0
    for request in requests:
        cost = request_cost(request["id"])
        note = "" if cost is not None else "price not found; counted as USD 0.01 to stay on the safe side"
        cost = 0.01 if cost is None else cost
        total += cost
        rows.append({"time": now, "step": step, "model": request.get("model", ""), "request_id": request["id"],
                     "cost_usd": f"{cost:.6f}", "note": note})
    if rows:
        _append(rows)
    return total


def note(step: str, cost_usd: float, text: str) -> None:
    """A cost that has no single request id, e.g. the 8.0 live test (estimated, on the safe side)."""
    _append([{"time": datetime.datetime.now().isoformat(timespec="seconds"), "step": step, "model": "", "request_id": "",
              "cost_usd": f"{cost_usd:.6f}", "note": text}])


def spent_usd() -> float:
    if not COST_LOG.exists():
        return 0.0
    with COST_LOG.open(encoding="utf-8") as handle:
        return sum(float(row["cost_usd"] or 0) for row in csv.DictReader(handle))


def check(forecast_usd: float = 0.0) -> None:
    """Raises BudgetExceeded if what is spent plus the forecast would pass the stop line."""
    spent = spent_usd()
    if spent + forecast_usd > STOP_USD:
        raise BudgetExceeded(f"spent USD {spent:.2f}; with the next USD {forecast_usd:.2f} this would pass the stop line "
                             f"of USD {STOP_USD:.2f} (EUR {STOP_USD / USD_PER_EUR:.2f}).")


def status() -> str:
    spent = spent_usd()
    return f"Spent so far: EUR {spent / USD_PER_EUR:.2f} of EUR {LIMIT_EUR:.0f} (USD {spent:.4f}; stop line USD {STOP_USD:.2f})"


def key_cross_check() -> str:
    """The key's own total since the start (includes other tools that use the same key)."""
    data = _get("https://openrouter.ai/api/v1/key")["data"]
    with (WORK / "key-checks.csv").open(encoding="utf-8") as handle:
        baseline = float(next(csv.DictReader(handle))["key_usage_usd"])
    return (f"Key total since the start: USD {data['usage'] - baseline:.4f} (also other tools); "
            f"left on the key: USD {data['limit_remaining']:.2f}")


if __name__ == "__main__":
    print(status())
    print(key_cross_check())
