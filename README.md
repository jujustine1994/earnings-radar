# earnings-radar

Automated pre/post-earnings tracking and preview-vs-actual comparison for US equities, powered by Claude.

- **Pre-earnings**: 1-2 days before a company's expected earnings date, generates a preview (via the `equity-research` plugin's `/earnings-preview`).
- **Post-earnings**: detects new SEC EDGAR filings (10-Q/10-K/8-K) and generates a summary, comparing actual results against the pre-earnings preview.
- Notifies via email; scheduled to run automatically (see `docs/superpowers/specs/`).

Design doc: [`docs/superpowers/specs/2026-07-08-us-earnings-auto-tracker-design.md`](docs/superpowers/specs/2026-07-08-us-earnings-auto-tracker-design.md)

`watchlist.json`, `state.json`, and `reports/` are gitignored — they contain the tracked ticker list and generated analysis, kept private even though this repo is public.
