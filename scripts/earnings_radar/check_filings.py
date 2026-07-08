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
