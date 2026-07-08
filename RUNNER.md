# Earnings Radar — Scheduled Run Instructions

Run this twice a day (before US market open, after US market close).

## 1. Check for due previews

Run: `python scripts/earnings_radar/check_previews.py --watchlist watchlist.json --state state.json`

For each item in the JSON array returned:
1. Use the `/earnings-preview` skill for `{ticker}` ({company_name}), earnings date {earnings_date}.
2. Draft the preview content. If no free consensus/estimate data is available, say so explicitly in the draft — do not omit the caveat.
3. Send the draft by email (Gmail MCP tool) to the user.
4. Save the draft to `reports/{ticker}/{earnings_date}-preview.md`.
5. Run: `python scripts/earnings_radar/update_state.py mark-preview-sent --state state.json --ticker {ticker} --earnings-date {earnings_date} --summary "<2-3 sentence summary of the key estimates/watch items from the preview>"`

## 2. Check for new filings

Run: `python scripts/earnings_radar/check_filings.py --watchlist watchlist.json --state state.json --contact-email you@example.com`

For each item in the JSON array returned:
1. Use the `/earnings` skill for `{ticker}` ({company_name}), filing {form} dated {filing_date} (accession {accession_number}).
2. Draft the summary, including a "Preview vs Actual" section:
   - If `preview_summary` is not null: restate what the preview expected, state what actually happened, call out the delta and a short read on beat/miss and why.
   - If `preview_summary` is null: state plainly that no preview was on file for this filing (either not tracked yet, or already compared) — do not fabricate a prior expectation.
3. Send the draft by email (Gmail MCP tool) to the user.
4. Save the draft to `reports/{ticker}/{filing_date}-filing-vs-preview.md`.
5. Run: `python scripts/earnings_radar/update_state.py mark-filing-compared --state state.json --ticker {ticker} --earnings-date {matched_earnings_date} --accession {accession_number}`
   (skip this step if `matched_earnings_date` is null — there's no cycle to mark, but still record the accession by running the same command with today's date as `--earnings-date` so future runs don't re-trigger on this filing... actually: if `matched_earnings_date` is null, run `mark-filing-compared` with `--earnings-date` set to `{filing_date}` instead, so `last_filing_accession` still gets updated.)

## 3. Error handling

If a script exits non-zero or a Nasdaq/SEC call inside `/earnings-preview` or `/earnings` fails for one ticker, append a line to `error.log` (`{timestamp} {ticker} {error}`) and continue to the next ticker — do not abort the whole run.
