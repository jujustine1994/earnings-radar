import argparse
import json
from datetime import date

from earnings_radar import nasdaq_calendar, state as state_mod, watchlist


def _has_recent_preview(state, ticker, earnings_date, window_days=5):
    """Return True if the ticker already has a preview_sent cycle within
    window_days of earnings_date (either direction).

    Guards against Nasdaq revising the predicted earnings date after a preview
    was already sent: the revised date would otherwise miss the exact-date cycle
    lookup and trigger a duplicate preview for the same earnings event.
    """
    cycles = state.get(ticker, {}).get("earnings_cycles", {})
    for cycle_date, cycle in cycles.items():
        if not cycle.get("preview_sent"):
            continue
        try:
            existing = date.fromisoformat(cycle_date)
        except ValueError:
            continue
        if abs((existing - earnings_date).days) <= window_days:
            return True
    return False


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
        if _has_recent_preview(state, entry["ticker"], earnings_date):
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
