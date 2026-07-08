# 美股財報自動追蹤系統 — Design

日期：2026-07-08

## 背景與目的

使用者是股票分析師，已安裝 Anthropic 官方 `financial-services` plugin marketplace 的
`financial-analysis` 與 `equity-research` 兩包（含 `/earnings`、`/earnings-preview` 等 skill）。
本專案目標：讓財報公開時（含財報前 preview、財報後 filing）自動觸發分析與通知，不需手動盯盤。

第一階段範圍：**僅美股**。台股（MOPS）留待後續階段，屆時需另外處理爬蟲穩定性問題。

## 範圍外（Out of scope，本階段不做）

- 台股 / 其他市場
- 付費 consensus 數據源（FactSet/Bloomberg/Refinitiv）串接 — 目前只用免費/非官方來源，
  抓不到市場預期時如實標註「無法比對市場預期」，不硬湊數字
- 即時（分鐘級）通知 — 本階段是排程輪詢，非 webhook 即時推播
- LINE/Slack 等其他通知管道 — 本階段只做 Email + 本機檔案

## 資料來源

| 用途 | 來源 | 性質 |
|---|---|---|
| 財報預估發布日期 | Nasdaq 公開財報日程頁面 | 免費、非官方，可能不穩定或日期微調 |
| 財報 filing 偵測 | SEC EDGAR `data.sec.gov/submissions/CIK##########.json` | 官方、免費、穩定 |
| 市場預期比對 | 免費/非官方來源（如可取得） | 覆蓋率不保證，抓不到就不比對，且需在輸出中明確標註 |

## 元件

### 1. `watchlist.json`
使用者維護的追蹤清單，欄位：`ticker`、`cik`（SEC 對應用）、`company_name`。
使用者可隨時請 Claude 增刪項目（不需要額外介面，直接對話請求修改此檔）。

### 2. `state.json`
記錄每檔股票、每個財報週期的狀態，避免重複通知並支援「preview vs 實際」對照。

結構（每個 ticker 一筆，每個財報日一筆歷史記錄）：
```json
{
  "AAPL": {
    "last_filing_accession": "0000320193-26-000012",
    "earnings_cycles": {
      "2026-07-30": {
        "preview_sent": true,
        "preview_summary": "<preview 產出的關鍵預估/關注重點，文字摘要>",
        "filing_compared": false
      }
    }
  }
}
```

### 3. 排程 Agent（Claude Code `/schedule`）
- 執行頻率：每天兩次（美股開盤前、收盤後）
- 兩條觸發線在同一次排程執行中依序跑完：Preview 檢查 → Filing 檢查

## 觸發邏輯

### A. 財報前 Preview
1. 對 `watchlist.json` 每檔股票，查 Nasdaq 日程取得下次財報預估日期
2. 若距離財報日剩 1-2 天，且 `state.json` 中該財報日 `preview_sent` 非 true：
   - 執行 `/earnings-preview` 邏輯（用抓得到的公開資料：歷史財報、股價、免費 estimate）
   - Email 寄出 + 存檔 `reports/<TICKER>/<財報日>-preview.md`
   - `state.json` 寫入該財報日：`preview_sent: true`、`preview_summary: <關鍵預估/關注重點摘要>`

### B. 財報後 Filing 摘要（含 Preview 對照）
1. 對每檔股票查 SEC EDGAR 最新 accession number，與 `state.json` 的 `last_filing_accession` 比對
2. 若有新的 10-Q/10-K/8-K：
   - 找出對應的 `earnings_cycles` 財報日紀錄（用公告日期就近比對財報日期）
   - 執行 `/earnings` 邏輯，內容包含：
     a. QoQ / YoY 比較
     b. **Preview 對照實際**：讀出該財報日的 `preview_summary`，逐項比對「preview 當初的預估/關注重點」vs「實際公告結果」，附差異與簡短判讀（優於/劣於預期、可能原因）
     c. 若當初 preview 沒有可比對的市場預期數據，如實註明
   - Email 寄出 + 存檔 `reports/<TICKER>/<財報日>-filing-vs-preview.md`
   - `state.json` 更新 `last_filing_accession`，該財報日 `filing_compared: true`

## 通知與輸出

- Email：透過使用者已連接的 Gmail MCP 寄送
- 本機留存：`reports/<TICKER>/` 下的 markdown 檔案，檔名含財報日期
- 每封 Email／檔案結尾附「資料來源與限制」免責聲明：標明哪些數字來自免費/非官方來源，
  以及是否有做到市場預期比對

## 錯誤處理

- Nasdaq 日程頁面抓取失敗、或 SEC CIK 對應不到 → 該檔股票本輪跳過，寫入 `error.log`
  （不中斷其他股票的處理），下次排程自動重試
- 不因單一股票失敗導致整個排程 job 失敗

## 測試 / 驗證方式

- 先用 1-2 檔已知近期有財報的美股（watchlist 手動加入）跑一次排程，人工核對：
  - Preview 是否在財報前 1-2 天正確觸發且只觸發一次
  - Filing 摘要是否正確抓到新 filing、正確從 state 撈出對應 preview 內容做對照
  - Email 與本機檔案是否都有正確產出
