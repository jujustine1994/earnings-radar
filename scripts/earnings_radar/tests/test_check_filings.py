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
