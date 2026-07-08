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
