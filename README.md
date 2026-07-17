規則檔: windows-tool.md

> **AI 注意（本專案為 windows-tool 的特例）：** 本專案是 Python 本機自動化腳本，
> 但**不是雙擊啟動**的工具——由 Claude Code `/schedule`（cron agent）驅動 CLI，
> 沒有 `<工具名>啟動器.bat` 也沒有 `launcher.ps1`，沒有 tkinter UI。
> `windows-tool.md` 的**啟動器與 bat 相關章節一律不適用**，不要為了合規而補建；
> 執行紀錄、文件規範、資安（例外處理不外洩金鑰）等其餘章節照常適用。
> 執行方式見 `RUNNER.md`。

# earnings-radar

Automated pre/post-earnings tracking and preview-vs-actual comparison for US equities, powered by Claude.

- **Pre-earnings**: 1-2 days before a company's expected earnings date, generates a preview (via the `equity-research` plugin's `/earnings-preview`).
- **Post-earnings**: detects new SEC EDGAR filings (10-Q/10-K/8-K) and generates a summary, comparing actual results against the pre-earnings preview.
- Notifies via email; scheduled to run automatically (see `docs/superpowers/specs/`).

Design doc: [`docs/superpowers/specs/2026-07-08-us-earnings-auto-tracker-design.md`](docs/superpowers/specs/2026-07-08-us-earnings-auto-tracker-design.md)

`watchlist.json`, `state.json`, and `reports/` are gitignored — they contain the tracked ticker list and generated analysis, kept private even though this repo is public.
