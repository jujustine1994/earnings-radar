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
