# US Earnings Auto-Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic data layer (watchlist/state management, SEC EDGAR filing detection, Nasdaq earnings-date lookup) that a scheduled Claude Code agent calls each run to decide whether to draft an earnings preview, draft a filing-vs-preview comparison, or do nothing.

**Architecture:** Small, independently-testable Python CLI scripts under `scripts/earnings_radar/`. Each script does one deterministic job and prints JSON to stdout — no scraping-fragile logic mixed with the analysis/writing step. The scheduled Claude agent (set up in the final task via `/schedule`) reads a script's JSON output, and when it says "trigger", the agent itself runs `/earnings-preview` or `/earnings`, drafts the email, sends it via the Gmail MCP tool, writes the report file, and finally calls `update_state.py` to record what happened. Claude does the writing/judgment; Python does the fetching/diffing/bookkeeping.

**Tech Stack:** Python 3.11+, `requests`, `pytest` + `responses` (HTTP mocking), stdlib `json`/`argparse`/`datetime`.

## Global Constraints

- `watchlist.json`, `state.json`, `reports/`, `error.log` are gitignored (spec: sensitive tracking data stays out of the public repo) — already set up in `.gitignore`.
- SEC EDGAR requires a descriptive `User-Agent` header on every request (SEC fair-access policy) — format: `"<app name> <contact email>"`.
- Nasdaq's earnings-calendar endpoint is an unofficial API; schema is not guaranteed — Task 3 includes a live-verification step before locking in the parser.
- No paid data sources. If market-expectation data can't be found, output must say so explicitly rather than omitting the field silently.
- Scope is US equities only for this plan.

---

### Task 1: Project scaffolding + watchlist module

**Files:**
- Create: `scripts/earnings_radar/__init__.py` (empty)
- Create: `scripts/earnings_radar/watchlist.py`
- Create: `watchlist.example.json`
- Create: `requirements.txt`
- Test: `scripts/earnings_radar/tests/test_watchlist.py`
- Test: `scripts/earnings_radar/tests/__init__.py` (empty)

**Interfaces:**
- Produces: `watchlist.load(path: str) -> list[dict]` — each dict has keys `ticker` (str), `cik` (str, 10-digit zero-padded), `company_name` (str). Raises `FileNotFoundError` if `path` doesn't exist.

- [ ] **Step 1: Write the failing test**

```python
# scripts/earnings_radar/tests/test_watchlist.py
import json
import pytest
from earnings_radar import watchlist


def test_load_returns_list_of_entries(tmp_path):
    data = [
        {"ticker": "AAPL", "cik": "0000320193", "company_name": "Apple Inc."}
    ]
    path = tmp_path / "watchlist.json"
    path.write_text(json.dumps(data))

    result = watchlist.load(str(path))

    assert result == data


def test_load_missing_file_raises(tmp_path):
    missing = tmp_path / "does_not_exist.json"

    with pytest.raises(FileNotFoundError):
        watchlist.load(str(missing))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_watchlist.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'earnings_radar'` or `AttributeError`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/earnings_radar/watchlist.py
import json


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_watchlist.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Create the example watchlist and requirements files**

```json
// watchlist.example.json (repo root)
[
  {
    "ticker": "AAPL",
    "cik": "0000320193",
    "company_name": "Apple Inc."
  }
]
```

```text
# requirements.txt (repo root)
requests>=2.31
pytest>=8.0
responses>=0.25
```

- [ ] **Step 6: Commit**

```bash
git add scripts/earnings_radar/__init__.py scripts/earnings_radar/watchlist.py \
        scripts/earnings_radar/tests/__init__.py scripts/earnings_radar/tests/test_watchlist.py \
        watchlist.example.json requirements.txt
git commit -m "feat: add watchlist loader with tests"
```

---

### Task 2: State module (read/update `state.json`)

**Files:**
- Create: `scripts/earnings_radar/state.py`
- Test: `scripts/earnings_radar/tests/test_state.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces:
  - `state.load(path: str) -> dict` — returns `{}` if file doesn't exist (first run).
  - `state.save(path: str, data: dict) -> None`
  - `state.get_cycle(state: dict, ticker: str, earnings_date: str) -> dict` — returns the cycle dict for that ticker+date, or `{}` if absent. Shape: `{"preview_sent": bool, "preview_summary": str, "filing_compared": bool}`.
  - `state.set_preview_sent(state: dict, ticker: str, earnings_date: str, summary: str) -> dict` — returns updated state (does not mutate in place... actually mutates and returns for convenience).
  - `state.set_last_filing_accession(state: dict, ticker: str, accession: str) -> dict`
  - `state.get_last_filing_accession(state: dict, ticker: str) -> str | None`
  - `state.set_filing_compared(state: dict, ticker: str, earnings_date: str) -> dict`

State shape on disk (matches design spec):
```json
{
  "AAPL": {
    "last_filing_accession": "0000320193-26-000012",
    "earnings_cycles": {
      "2026-07-30": {
        "preview_sent": true,
        "preview_summary": "...",
        "filing_compared": false
      }
    }
  }
}
```

- [ ] **Step 1: Write the failing test**

```python
# scripts/earnings_radar/tests/test_state.py
import json
from earnings_radar import state


def test_load_missing_file_returns_empty_dict(tmp_path):
    missing = tmp_path / "state.json"
    assert state.load(str(missing)) == {}


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    data = {"AAPL": {"last_filing_accession": "0001", "earnings_cycles": {}}}

    state.save(str(path), data)

    assert state.load(str(path)) == data


def test_set_preview_sent_creates_cycle():
    s = {}
    s = state.set_preview_sent(s, "AAPL", "2026-07-30", "Expect EPS ~$1.50")

    cycle = state.get_cycle(s, "AAPL", "2026-07-30")
    assert cycle == {
        "preview_sent": True,
        "preview_summary": "Expect EPS ~$1.50",
        "filing_compared": False,
    }


def test_get_cycle_missing_returns_empty_dict():
    assert state.get_cycle({}, "AAPL", "2026-07-30") == {}


def test_last_filing_accession_roundtrip():
    s = {}
    s = state.set_last_filing_accession(s, "AAPL", "0000320193-26-000012")

    assert state.get_last_filing_accession(s, "AAPL") == "0000320193-26-000012"


def test_get_last_filing_accession_missing_returns_none():
    assert state.get_last_filing_accession({}, "AAPL") is None


def test_set_filing_compared_updates_existing_cycle():
    s = state.set_preview_sent({}, "AAPL", "2026-07-30", "summary")
    s = state.set_filing_compared(s, "AAPL", "2026-07-30")

    cycle = state.get_cycle(s, "AAPL", "2026-07-30")
    assert cycle["filing_compared"] is True
    assert cycle["preview_summary"] == "summary"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'earnings_radar.state'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/earnings_radar/state.py
import json
import os


def load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path: str, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _ensure_ticker(state: dict, ticker: str) -> dict:
    return state.setdefault(ticker, {"last_filing_accession": None, "earnings_cycles": {}})


def get_cycle(state: dict, ticker: str, earnings_date: str) -> dict:
    return state.get(ticker, {}).get("earnings_cycles", {}).get(earnings_date, {})


def set_preview_sent(state: dict, ticker: str, earnings_date: str, summary: str) -> dict:
    entry = _ensure_ticker(state, ticker)
    entry["earnings_cycles"][earnings_date] = {
        "preview_sent": True,
        "preview_summary": summary,
        "filing_compared": False,
    }
    return state


def set_filing_compared(state: dict, ticker: str, earnings_date: str) -> dict:
    entry = _ensure_ticker(state, ticker)
    cycle = entry["earnings_cycles"].setdefault(
        earnings_date, {"preview_sent": False, "preview_summary": "", "filing_compared": False}
    )
    cycle["filing_compared"] = True
    return state


def get_last_filing_accession(state: dict, ticker: str) -> str | None:
    return state.get(ticker, {}).get("last_filing_accession")


def set_last_filing_accession(state: dict, ticker: str, accession: str) -> dict:
    entry = _ensure_ticker(state, ticker)
    entry["last_filing_accession"] = accession
    return state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_state.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/earnings_radar/state.py scripts/earnings_radar/tests/test_state.py
git commit -m "feat: add state module for preview/filing tracking"
```

---

### Task 3: Nasdaq earnings-date lookup

**Files:**
- Create: `scripts/earnings_radar/nasdaq_calendar.py`
- Test: `scripts/earnings_radar/tests/test_nasdaq_calendar.py`

**Interfaces:**
- Produces: `nasdaq_calendar.fetch_next_earnings_date(ticker: str, today: date, session=None, max_days_ahead: int = 120) -> date | None`
  - Queries Nasdaq's public per-day earnings calendar (`https://api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD`) day by day starting from `today`, looking for `ticker` in that day's rows, up to `max_days_ahead` days out. Returns the first matching date, or `None` if not found.
  - `session` param lets tests inject a fake HTTP client; production code defaults to `requests`.

**Before writing the parser, verify the live schema (do this once, manually, not as an automated test):**

```bash
curl -s "https://api.nasdaq.com/api/calendar/earnings?date=$(date +%F)" \
  -H "User-Agent: Mozilla/5.0" -H "Accept: application/json" | head -c 2000
```

Confirm the response has a `data.rows` array where each row has a `symbol` field (Nasdaq has changed field casing before, e.g. `symbol` vs `symbol_link`). If the shape differs from what's coded below, adjust `_extract_symbols` accordingly before proceeding — this is a required correction step, not optional polish.

- [ ] **Step 1: Write the failing test**

```python
# scripts/earnings_radar/tests/test_nasdaq_calendar.py
from datetime import date
from unittest.mock import Mock
from earnings_radar import nasdaq_calendar


def _fake_response(symbols):
    resp = Mock()
    resp.status_code = 200
    resp.json.return_value = {"data": {"rows": [{"symbol": s} for s in symbols]}}
    return resp


def test_finds_ticker_on_first_day_checked():
    session = Mock()
    session.get.return_value = _fake_response(["AAPL", "MSFT"])

    result = nasdaq_calendar.fetch_next_earnings_date("AAPL", date(2026, 7, 28), session=session)

    assert result == date(2026, 7, 28)
    assert session.get.call_count == 1


def test_finds_ticker_on_later_day():
    session = Mock()
    session.get.side_effect = [
        _fake_response(["MSFT"]),
        _fake_response(["GOOG"]),
        _fake_response(["AAPL"]),
    ]

    result = nasdaq_calendar.fetch_next_earnings_date(
        "AAPL", date(2026, 7, 28), session=session, max_days_ahead=5
    )

    assert result == date(2026, 7, 30)


def test_returns_none_when_not_found_within_window():
    session = Mock()
    session.get.return_value = _fake_response(["MSFT"])

    result = nasdaq_calendar.fetch_next_earnings_date(
        "AAPL", date(2026, 7, 28), session=session, max_days_ahead=3
    )

    assert result is None
    assert session.get.call_count == 3


def test_skips_day_on_malformed_response():
    session = Mock()
    bad_resp = Mock()
    bad_resp.status_code = 200
    bad_resp.json.return_value = {"data": None}
    session.get.side_effect = [bad_resp, _fake_response(["AAPL"])]

    result = nasdaq_calendar.fetch_next_earnings_date(
        "AAPL", date(2026, 7, 28), session=session, max_days_ahead=5
    )

    assert result == date(2026, 7, 29)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_nasdaq_calendar.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'earnings_radar.nasdaq_calendar'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/earnings_radar/nasdaq_calendar.py
from datetime import date, timedelta

import requests

_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
_URL = "https://api.nasdaq.com/api/calendar/earnings"


def _extract_symbols(payload: dict) -> list[str]:
    data = payload.get("data") or {}
    rows = data.get("rows") or []
    return [row.get("symbol") for row in rows if row.get("symbol")]


def fetch_next_earnings_date(
    ticker: str, today: date, session=None, max_days_ahead: int = 120
) -> date | None:
    http = session or requests
    for offset in range(max_days_ahead):
        day = today + timedelta(days=offset)
        response = http.get(_URL, params={"date": day.isoformat()}, headers=_HEADERS)
        if response.status_code != 200:
            continue
        symbols = _extract_symbols(response.json())
        if ticker in symbols:
            return day
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_nasdaq_calendar.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/earnings_radar/nasdaq_calendar.py scripts/earnings_radar/tests/test_nasdaq_calendar.py
git commit -m "feat: add Nasdaq earnings-date lookup"
```

---

### Task 4: SEC EDGAR filing lookup

**Files:**
- Create: `scripts/earnings_radar/sec_edgar.py`
- Test: `scripts/earnings_radar/tests/test_sec_edgar.py`

**Interfaces:**
- Produces: `sec_edgar.fetch_latest_filing(cik: str, session=None, contact_email: str = "you@example.com", forms=("10-Q", "10-K", "8-K")) -> dict | None`
  - Hits `https://data.sec.gov/submissions/CIK{cik}.json` (cik must already be the 10-digit zero-padded string).
  - Returns the most recent filing (by filing date) whose form is in `forms`, as `{"accession_number": str, "form": str, "filing_date": str}`, or `None` if none found.
  - Sets `User-Agent` header to `"earnings-radar {contact_email}"` per SEC's fair-access policy.

- [ ] **Step 1: Write the failing test**

```python
# scripts/earnings_radar/tests/test_sec_edgar.py
from unittest.mock import Mock
from earnings_radar import sec_edgar


def _fake_submissions(forms, dates, accessions):
    resp = Mock()
    resp.status_code = 200
    resp.json.return_value = {
        "filings": {
            "recent": {
                "form": forms,
                "filingDate": dates,
                "accessionNumber": accessions,
            }
        }
    }
    return resp


def test_returns_most_recent_matching_form():
    session = Mock()
    session.get.return_value = _fake_submissions(
        forms=["4", "10-Q", "8-K"],
        dates=["2026-07-01", "2026-06-30", "2026-07-30"],
        accessions=["a-1", "a-2", "a-3"],
    )

    result = sec_edgar.fetch_latest_filing("0000320193", session=session)

    assert result == {"accession_number": "a-3", "form": "8-K", "filing_date": "2026-07-30"}


def test_returns_none_when_no_matching_form():
    session = Mock()
    session.get.return_value = _fake_submissions(
        forms=["4", "3"], dates=["2026-07-01", "2026-06-30"], accessions=["a-1", "a-2"]
    )

    result = sec_edgar.fetch_latest_filing("0000320193", session=session)

    assert result is None


def test_sends_required_user_agent_header():
    session = Mock()
    session.get.return_value = _fake_submissions(forms=[], dates=[], accessions=[])

    sec_edgar.fetch_latest_filing("0000320193", session=session, contact_email="me@x.com")

    _, kwargs = session.get.call_args
    assert "me@x.com" in kwargs["headers"]["User-Agent"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_sec_edgar.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'earnings_radar.sec_edgar'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/earnings_radar/sec_edgar.py
import requests

_URL_TEMPLATE = "https://data.sec.gov/submissions/CIK{cik}.json"


def fetch_latest_filing(
    cik: str,
    session=None,
    contact_email: str = "you@example.com",
    forms=("10-Q", "10-K", "8-K"),
) -> dict | None:
    http = session or requests
    headers = {"User-Agent": f"earnings-radar {contact_email}"}
    response = http.get(_URL_TEMPLATE.format(cik=cik), headers=headers)
    response.raise_for_status()

    recent = response.json().get("filings", {}).get("recent", {})
    candidates = [
        {
            "accession_number": recent["accessionNumber"][i],
            "form": recent["form"][i],
            "filing_date": recent["filingDate"][i],
        }
        for i in range(len(recent.get("form", [])))
        if recent["form"][i] in forms
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda c: c["filing_date"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_sec_edgar.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/earnings_radar/sec_edgar.py scripts/earnings_radar/tests/test_sec_edgar.py
git commit -m "feat: add SEC EDGAR latest-filing lookup"
```

---

### Task 5: `check_previews.py` CLI

**Files:**
- Create: `scripts/earnings_radar/check_previews.py`
- Test: `scripts/earnings_radar/tests/test_check_previews.py`

**Interfaces:**
- Consumes: `watchlist.load` (Task 1), `state.load` / `state.get_cycle` (Task 2), `nasdaq_calendar.fetch_next_earnings_date` (Task 3).
- Produces: `check_previews.find_due_previews(watchlist_entries: list[dict], state: dict, today: date, calendar_fn) -> list[dict]`
  - `calendar_fn` has signature `(ticker: str, today: date) -> date | None` (allows injecting a fake in tests instead of hitting Nasdaq).
  - Returns a list of `{"ticker": str, "cik": str, "company_name": str, "earnings_date": str}` for every watchlist entry where the earnings date is 1 or 2 days from `today` AND `state.get_cycle(...).get("preview_sent")` is not `True`.
  - CLI entry point (`if __name__ == "__main__"`) reads `watchlist.json` and `state.json` paths from `argparse`, calls `find_due_previews` using the real `nasdaq_calendar.fetch_next_earnings_date`, and prints the result list as JSON to stdout.

- [ ] **Step 1: Write the failing test**

```python
# scripts/earnings_radar/tests/test_check_previews.py
from datetime import date
from earnings_radar import check_previews


def test_includes_ticker_one_day_before_earnings():
    watchlist_entries = [{"ticker": "AAPL", "cik": "0000320193", "company_name": "Apple Inc."}]
    state = {}
    today = date(2026, 7, 28)

    def calendar_fn(ticker, today):
        return date(2026, 7, 29)

    result = check_previews.find_due_previews(watchlist_entries, state, today, calendar_fn)

    assert result == [
        {
            "ticker": "AAPL",
            "cik": "0000320193",
            "company_name": "Apple Inc.",
            "earnings_date": "2026-07-29",
        }
    ]


def test_excludes_ticker_too_far_out():
    watchlist_entries = [{"ticker": "AAPL", "cik": "0000320193", "company_name": "Apple Inc."}]
    state = {}
    today = date(2026, 7, 1)

    def calendar_fn(ticker, today):
        return date(2026, 7, 29)

    result = check_previews.find_due_previews(watchlist_entries, state, today, calendar_fn)

    assert result == []


def test_excludes_ticker_already_previewed():
    watchlist_entries = [{"ticker": "AAPL", "cik": "0000320193", "company_name": "Apple Inc."}]
    state = {"AAPL": {"earnings_cycles": {"2026-07-29": {"preview_sent": True}}}}
    today = date(2026, 7, 28)

    def calendar_fn(ticker, today):
        return date(2026, 7, 29)

    result = check_previews.find_due_previews(watchlist_entries, state, today, calendar_fn)

    assert result == []


def test_excludes_ticker_with_no_known_earnings_date():
    watchlist_entries = [{"ticker": "AAPL", "cik": "0000320193", "company_name": "Apple Inc."}]
    state = {}
    today = date(2026, 7, 28)

    def calendar_fn(ticker, today):
        return None

    result = check_previews.find_due_previews(watchlist_entries, state, today, calendar_fn)

    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_check_previews.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'earnings_radar.check_previews'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/earnings_radar/check_previews.py
import argparse
import json
from datetime import date

from earnings_radar import nasdaq_calendar, state as state_mod, watchlist


def find_due_previews(watchlist_entries, state, today, calendar_fn):
    due = []
    for entry in watchlist_entries:
        earnings_date = calendar_fn(entry["ticker"], today)
        if earnings_date is None:
            continue
        days_out = (earnings_date - today).days
        if days_out not in (1, 2):
            continue
        cycle = state_mod.get_cycle(state, entry["ticker"], earnings_date.isoformat())
        if cycle.get("preview_sent"):
            continue
        due.append(
            {
                "ticker": entry["ticker"],
                "cik": entry["cik"],
                "company_name": entry["company_name"],
                "earnings_date": earnings_date.isoformat(),
            }
        )
    return due


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchlist", default="watchlist.json")
    parser.add_argument("--state", default="state.json")
    args = parser.parse_args()

    entries = watchlist.load(args.watchlist)
    current_state = state_mod.load(args.state)
    result = find_due_previews(
        entries, current_state, date.today(), nasdaq_calendar.fetch_next_earnings_date
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_check_previews.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/earnings_radar/check_previews.py scripts/earnings_radar/tests/test_check_previews.py
git commit -m "feat: add check_previews CLI for pre-earnings trigger detection"
```

---

### Task 6: `check_filings.py` CLI

**Files:**
- Create: `scripts/earnings_radar/check_filings.py`
- Test: `scripts/earnings_radar/tests/test_check_filings.py`

**Interfaces:**
- Consumes: `watchlist.load` (Task 1), `state.load` / `state.get_last_filing_accession` / `state.get_cycle` (Task 2), `sec_edgar.fetch_latest_filing` (Task 4).
- Produces: `check_filings.find_new_filings(watchlist_entries: list[dict], state: dict, filing_fn) -> list[dict]`
  - `filing_fn` has signature `(cik: str) -> dict | None` (matches `sec_edgar.fetch_latest_filing` with `cik` bound).
  - Returns a list of `{"ticker": str, "cik": str, "company_name": str, "accession_number": str, "form": str, "filing_date": str, "matched_earnings_date": str | None, "preview_summary": str | None}` for every watchlist entry where the latest filing's accession number differs from `state`'s recorded `last_filing_accession` (or there's no recorded accession yet).
  - `matched_earnings_date` / `preview_summary`: look through the ticker's `earnings_cycles` in `state` for the entry with `preview_sent: True` and `filing_compared: False`; if found, use its date/summary — otherwise both are `None`.
  - CLI entry point mirrors Task 5's pattern, using `sec_edgar.fetch_latest_filing` bound via a small wrapper lambda.

- [ ] **Step 1: Write the failing test**

```python
# scripts/earnings_radar/tests/test_check_filings.py
from earnings_radar import check_filings


def test_includes_ticker_with_new_accession_and_matches_preview():
    watchlist_entries = [{"ticker": "AAPL", "cik": "0000320193", "company_name": "Apple Inc."}]
    state = {
        "AAPL": {
            "last_filing_accession": "old-1",
            "earnings_cycles": {
                "2026-07-29": {
                    "preview_sent": True,
                    "preview_summary": "Expect EPS ~$1.50",
                    "filing_compared": False,
                }
            },
        }
    }

    def filing_fn(cik):
        return {"accession_number": "new-2", "form": "8-K", "filing_date": "2026-07-30"}

    result = check_filings.find_new_filings(watchlist_entries, state, filing_fn)

    assert result == [
        {
            "ticker": "AAPL",
            "cik": "0000320193",
            "company_name": "Apple Inc.",
            "accession_number": "new-2",
            "form": "8-K",
            "filing_date": "2026-07-30",
            "matched_earnings_date": "2026-07-29",
            "preview_summary": "Expect EPS ~$1.50",
        }
    ]


def test_excludes_ticker_with_same_accession():
    watchlist_entries = [{"ticker": "AAPL", "cik": "0000320193", "company_name": "Apple Inc."}]
    state = {"AAPL": {"last_filing_accession": "same-1", "earnings_cycles": {}}}

    def filing_fn(cik):
        return {"accession_number": "same-1", "form": "8-K", "filing_date": "2026-07-30"}

    result = check_filings.find_new_filings(watchlist_entries, state, filing_fn)

    assert result == []


def test_includes_ticker_with_no_prior_accession():
    watchlist_entries = [{"ticker": "AAPL", "cik": "0000320193", "company_name": "Apple Inc."}]
    state = {}

    def filing_fn(cik):
        return {"accession_number": "first-1", "form": "10-Q", "filing_date": "2026-07-30"}

    result = check_filings.find_new_filings(watchlist_entries, state, filing_fn)

    assert result[0]["accession_number"] == "first-1"
    assert result[0]["matched_earnings_date"] is None
    assert result[0]["preview_summary"] is None


def test_excludes_ticker_when_sec_returns_none():
    watchlist_entries = [{"ticker": "AAPL", "cik": "0000320193", "company_name": "Apple Inc."}]
    state = {}

    def filing_fn(cik):
        return None

    result = check_filings.find_new_filings(watchlist_entries, state, filing_fn)

    assert result == []


def test_ignores_already_compared_cycle():
    watchlist_entries = [{"ticker": "AAPL", "cik": "0000320193", "company_name": "Apple Inc."}]
    state = {
        "AAPL": {
            "last_filing_accession": "old-1",
            "earnings_cycles": {
                "2026-07-29": {
                    "preview_sent": True,
                    "preview_summary": "Expect EPS ~$1.50",
                    "filing_compared": True,
                }
            },
        }
    }

    def filing_fn(cik):
        return {"accession_number": "new-2", "form": "8-K", "filing_date": "2026-07-30"}

    result = check_filings.find_new_filings(watchlist_entries, state, filing_fn)

    assert result[0]["matched_earnings_date"] is None
    assert result[0]["preview_summary"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_check_filings.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'earnings_radar.check_filings'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/earnings_radar/check_filings.py
import argparse
import json

from earnings_radar import sec_edgar, state as state_mod, watchlist


def _find_pending_preview(state: dict, ticker: str) -> tuple[str | None, str | None]:
    cycles = state.get(ticker, {}).get("earnings_cycles", {})
    for earnings_date, cycle in cycles.items():
        if cycle.get("preview_sent") and not cycle.get("filing_compared"):
            return earnings_date, cycle.get("preview_summary")
    return None, None


def find_new_filings(watchlist_entries, state, filing_fn):
    new_filings = []
    for entry in watchlist_entries:
        filing = filing_fn(entry["cik"])
        if filing is None:
            continue
        last_accession = state_mod.get_last_filing_accession(state, entry["ticker"])
        if filing["accession_number"] == last_accession:
            continue
        matched_earnings_date, preview_summary = _find_pending_preview(state, entry["ticker"])
        new_filings.append(
            {
                "ticker": entry["ticker"],
                "cik": entry["cik"],
                "company_name": entry["company_name"],
                "accession_number": filing["accession_number"],
                "form": filing["form"],
                "filing_date": filing["filing_date"],
                "matched_earnings_date": matched_earnings_date,
                "preview_summary": preview_summary,
            }
        )
    return new_filings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watchlist", default="watchlist.json")
    parser.add_argument("--state", default="state.json")
    parser.add_argument("--contact-email", default="you@example.com")
    args = parser.parse_args()

    entries = watchlist.load(args.watchlist)
    current_state = state_mod.load(args.state)
    result = find_new_filings(
        entries,
        current_state,
        lambda cik: sec_edgar.fetch_latest_filing(cik, contact_email=args.contact_email),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_check_filings.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/earnings_radar/check_filings.py scripts/earnings_radar/tests/test_check_filings.py
git commit -m "feat: add check_filings CLI for post-earnings trigger detection"
```

---

### Task 7: `update_state.py` CLI

**Files:**
- Create: `scripts/earnings_radar/update_state.py`
- Test: `scripts/earnings_radar/tests/test_update_state.py`

**Interfaces:**
- Consumes: `state.load` / `state.save` / `state.set_preview_sent` / `state.set_filing_compared` / `state.set_last_filing_accession` (Task 2).
- Produces: CLI with two subcommands, invoked by the scheduled agent after it finishes drafting/sending:
  - `python update_state.py mark-preview-sent --state state.json --ticker AAPL --earnings-date 2026-07-29 --summary "Expect EPS ~$1.50"`
  - `python update_state.py mark-filing-compared --state state.json --ticker AAPL --earnings-date 2026-07-29 --accession new-2`
    (this subcommand calls both `set_filing_compared` and `set_last_filing_accession`)
  - Both subcommands load state, apply the mutation, and save — function `apply_command(args: argparse.Namespace) -> dict` returns the resulting state dict so it's testable without going through `sys.argv`.

- [ ] **Step 1: Write the failing test**

```python
# scripts/earnings_radar/tests/test_update_state.py
import argparse
from earnings_radar import update_state


def _args(**kwargs):
    defaults = {
        "command": None,
        "state": None,
        "ticker": None,
        "earnings_date": None,
        "summary": None,
        "accession": None,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_mark_preview_sent(tmp_path):
    state_path = str(tmp_path / "state.json")
    args = _args(
        command="mark-preview-sent",
        state=state_path,
        ticker="AAPL",
        earnings_date="2026-07-29",
        summary="Expect EPS ~$1.50",
    )

    result = update_state.apply_command(args)

    cycle = result["AAPL"]["earnings_cycles"]["2026-07-29"]
    assert cycle["preview_sent"] is True
    assert cycle["preview_summary"] == "Expect EPS ~$1.50"


def test_mark_filing_compared(tmp_path):
    state_path = str(tmp_path / "state.json")
    update_state.apply_command(
        _args(
            command="mark-preview-sent",
            state=state_path,
            ticker="AAPL",
            earnings_date="2026-07-29",
            summary="Expect EPS ~$1.50",
        )
    )

    result = update_state.apply_command(
        _args(
            command="mark-filing-compared",
            state=state_path,
            ticker="AAPL",
            earnings_date="2026-07-29",
            accession="new-2",
        )
    )

    cycle = result["AAPL"]["earnings_cycles"]["2026-07-29"]
    assert cycle["filing_compared"] is True
    assert result["AAPL"]["last_filing_accession"] == "new-2"


def test_state_persists_to_disk(tmp_path):
    state_path = str(tmp_path / "state.json")
    update_state.apply_command(
        _args(
            command="mark-preview-sent",
            state=state_path,
            ticker="AAPL",
            earnings_date="2026-07-29",
            summary="s",
        )
    )

    from earnings_radar import state as state_mod

    reloaded = state_mod.load(state_path)
    assert reloaded["AAPL"]["earnings_cycles"]["2026-07-29"]["preview_sent"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_update_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'earnings_radar.update_state'`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/earnings_radar/update_state.py
import argparse

from earnings_radar import state as state_mod


def apply_command(args) -> dict:
    current_state = state_mod.load(args.state)

    if args.command == "mark-preview-sent":
        current_state = state_mod.set_preview_sent(
            current_state, args.ticker, args.earnings_date, args.summary
        )
    elif args.command == "mark-filing-compared":
        current_state = state_mod.set_filing_compared(current_state, args.ticker, args.earnings_date)
        current_state = state_mod.set_last_filing_accession(current_state, args.ticker, args.accession)
    else:
        raise ValueError(f"Unknown command: {args.command}")

    state_mod.save(args.state, current_state)
    return current_state


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    preview = subparsers.add_parser("mark-preview-sent")
    preview.add_argument("--state", default="state.json")
    preview.add_argument("--ticker", required=True)
    preview.add_argument("--earnings-date", required=True)
    preview.add_argument("--summary", required=True)

    filing = subparsers.add_parser("mark-filing-compared")
    filing.add_argument("--state", default="state.json")
    filing.add_argument("--ticker", required=True)
    filing.add_argument("--earnings-date", required=True)
    filing.add_argument("--accession", required=True)

    args = parser.parse_args()
    apply_command(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd scripts/earnings_radar && python -m pytest tests/test_update_state.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/earnings_radar/update_state.py scripts/earnings_radar/tests/test_update_state.py
git commit -m "feat: add update_state CLI for recording preview/filing outcomes"
```

---

### Task 8: Runner instructions + `/schedule` setup

**Files:**
- Create: `RUNNER.md`
- Modify: nothing else (this task is prose + interactive setup, no new Python)

**Interfaces:**
- Consumes: all CLI scripts from Tasks 5-7 (`check_previews.py`, `check_filings.py`, `update_state.py`).
- Produces: nothing consumed by later tasks — this is the last task.

**RUNNER.md content** (this is what the scheduled Claude agent reads each run):

```markdown
# Earnings Radar — Scheduled Run Instructions

Run this twice a day (before US market open, after US market close).

## 1. Check for due previews

Run: `python scripts/earnings_radar/check_previews.py --watchlist watchlist.json --state state.json`

For each item in the JSON array returned:
1. Use the `/earnings-preview` skill for `{ticker}` ({company_name}), earnings date {earnings_date}.
2. Draft the preview content. If no free consensus/estimate data is available, say so explicitly in the draft — do not omit the caveat.
3. Send the draft by email (Gmail MCP tool) to the user.
4. Save the draft to `reports/{ticker}/{earnings_date}-preview.md`.
5. Run: `python scripts/earnings_radar/update_state.py mark-preview-sent --state state.json --ticker {ticker} --earnings-date {earnings_date} --summary "<2-3 sentence summary of the key estimates/watch items from the preview>"`

## 2. Check for new filings

Run: `python scripts/earnings_radar/check_filings.py --watchlist watchlist.json --state state.json --contact-email you@example.com`

For each item in the JSON array returned:
1. Use the `/earnings` skill for `{ticker}` ({company_name}), filing {form} dated {filing_date} (accession {accession_number}).
2. Draft the summary, including a "Preview vs Actual" section:
   - If `preview_summary` is not null: restate what the preview expected, state what actually happened, call out the delta and a short read on beat/miss and why.
   - If `preview_summary` is null: state plainly that no preview was on file for this filing (either not tracked yet, or already compared) — do not fabricate a prior expectation.
3. Send the draft by email (Gmail MCP tool) to the user.
4. Save the draft to `reports/{ticker}/{filing_date}-filing-vs-preview.md`.
5. Run: `python scripts/earnings_radar/update_state.py mark-filing-compared --state state.json --ticker {ticker} --earnings-date {matched_earnings_date} --accession {accession_number}`
   (skip this step if `matched_earnings_date` is null — there's no cycle to mark, but still record the accession by running the same command with today's date as `--earnings-date` so future runs don't re-trigger on this filing... actually: if `matched_earnings_date` is null, run `mark-filing-compared` with `--earnings-date` set to `{filing_date}` instead, so `last_filing_accession` still gets updated.)

## 3. Error handling

If a script exits non-zero or a Nasdaq/SEC call inside `/earnings-preview` or `/earnings` fails for one ticker, append a line to `error.log` (`{timestamp} {ticker} {error}`) and continue to the next ticker — do not abort the whole run.
```

- [ ] **Step 1: Write `RUNNER.md`** with the exact content above.

- [ ] **Step 2: Commit**

```bash
git add RUNNER.md
git commit -m "docs: add scheduled-run instructions for earnings radar"
```

- [ ] **Step 3: Populate real config (manual, not committed)**

```bash
cp watchlist.example.json watchlist.json
# edit watchlist.json to add real tickers you want to track
```

- [ ] **Step 4: Set up the schedule**

Use the `schedule` skill / `/schedule` command to create a routine that runs twice daily (e.g. `0 8,21 * * 1-5` in your timezone, adjusted for US pre-market/post-close) with the prompt: "Follow the instructions in RUNNER.md in this repo." Confirm the routine is created and do one manual trigger to verify end-to-end before trusting the automatic schedule.

---

## Self-Review Notes

- **Spec coverage:** watchlist mgmt (Task 1), state incl. preview_summary for diffing (Task 2), Nasdaq date lookup (Task 3), SEC filing detection (Task 4), preview trigger window 1-2 days (Task 5), filing trigger + preview linkage (Task 6), state mutation CLI used by the agent (Task 7), scheduling + email + report files + error handling + preview-vs-actual comparison wiring (Task 8/RUNNER.md). All design spec sections are covered.
- **Placeholder scan:** no TBD/TODO left; the one open item (Nasdaq JSON schema) is called out as a required verification step with an exact `curl` command, not a deferred implementation gap.
- **Type consistency:** `ticker`/`cik`/`company_name`/`earnings_date` (ISO string) keys are used consistently across Tasks 1, 5, 6, 8. `accession_number` (not `accessionNumber`) is used consistently from Task 4 onward after translation out of the raw SEC field name.
