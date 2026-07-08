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
