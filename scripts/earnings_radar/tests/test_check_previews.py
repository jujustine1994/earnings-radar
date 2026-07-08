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
