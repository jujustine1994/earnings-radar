# Earnings Radar — Scheduled Run Instructions

Run this twice a day (before US market open, after US market close).

**Working directory & imports:** Run all commands below from the repo root with `PYTHONPATH=scripts` set. The scripts use absolute imports (`from earnings_radar import ...`), so running them by bare file path (e.g. `python scripts/earnings_radar/check_previews.py`) fails with `ModuleNotFoundError: No module named 'earnings_radar'` — Python puts the script's own directory on the path, not `scripts/`. Setting `PYTHONPATH=scripts` puts `scripts/` on the import path so `earnings_radar` resolves. Each command below already includes the prefix.

## Before enabling the schedule (first-time setup)

When you add new tickers to `watchlist.json`, prime the state before turning the schedule on. `check_filings.py` treats "no prior recorded accession" as a new filing, so a fresh watchlist of N tickers would otherwise fan out N filing emails on the first scheduled run — surfacing each company's most recent historical filing (possibly months old, with no preview to compare against) as if it were new.

To start "already caught up":

1. Run the filing check once manually:
   `PYTHONPATH=scripts python scripts/earnings_radar/check_filings.py --watchlist watchlist.json --state state.json --contact-email you@example.com`
2. For each result in the returned JSON array, record the accession immediately — do NOT draft or email anything:
   `PYTHONPATH=scripts python scripts/earnings_radar/update_state.py mark-filing-compared --state state.json --ticker {ticker} --earnings-date {filing_date} --accession {accession_number}`

After this, the schedule starts from a clean baseline and only new filings that arrive after setup will trigger summaries.

## 1. Check for due previews

Run: `PYTHONPATH=scripts python scripts/earnings_radar/check_previews.py --watchlist watchlist.json --state state.json`

For each item in the JSON array returned:
1. Use the `/earnings-preview` skill for `{ticker}` ({company_name}), earnings date {earnings_date}.
2. Draft the preview content. If no free consensus/estimate data is available, say so explicitly in the draft — do not omit the caveat.
3. Send the draft by email (Gmail MCP tool) to the user.
4. Save the draft to `reports/{ticker}/{earnings_date}-preview.md`.
5. Run: `PYTHONPATH=scripts python scripts/earnings_radar/update_state.py mark-preview-sent --state state.json --ticker {ticker} --earnings-date {earnings_date} --summary "<2-3 sentence summary of the key estimates/watch items from the preview>"`

## 2. Check for new filings

Run: `PYTHONPATH=scripts python scripts/earnings_radar/check_filings.py --watchlist watchlist.json --state state.json --contact-email you@example.com`

For each item in the JSON array returned:
1. Use the `/earnings` skill for `{ticker}` ({company_name}), filing {form} dated {filing_date} (accession {accession_number}).
2. Draft the summary, including a "Preview vs Actual" section:
   - If `preview_summary` is not null: restate what the preview expected, state what actually happened, call out the delta and a short read on beat/miss and why.
   - If `preview_summary` is null: state plainly that no preview was on file for this filing (either not tracked yet, or already compared) — do not fabricate a prior expectation.
3. Send the draft by email (Gmail MCP tool) to the user.
4. Save the draft to `reports/{ticker}/{filing_date}-filing-vs-preview.md`.
5. Run `update_state.py mark-filing-compared` to persist the outcome:
   - If `matched_earnings_date` is not null, use it as `--earnings-date`.
   - If `matched_earnings_date` is null (no pending preview to mark), use `{filing_date}` as `--earnings-date` instead — this still records the new accession so future runs don't re-trigger on this same filing.
   - `PYTHONPATH=scripts python scripts/earnings_radar/update_state.py mark-filing-compared --state state.json --ticker {ticker} --earnings-date <as above> --accession {accession_number}`

## 3. Error handling

If a script exits non-zero or a Nasdaq/SEC call inside `/earnings-preview` or `/earnings` fails for one ticker, append a line to `error.log` (`{timestamp} {ticker} {error}`) and continue to the next ticker — do not abort the whole run.
