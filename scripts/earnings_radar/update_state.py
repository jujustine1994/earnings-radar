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
