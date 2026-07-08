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
