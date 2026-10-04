# ComputAI v0.1.0-beta.3

**只打 `computai`，就知道可以做什麼。** 這版把主要功能放進選單，並提供從安裝到下載月報圖卡的直接路徑。

## 這版新增

- **功能選單**：即時監控、月報圖卡、網頁監控、花費分析、資料來源檢查與環境設定。
  輸入數字後按 Enter；直接 Enter 進監控，`0` 或 `q` 離開。監控內按 `h` 或 `?` 看說明、`c` 開製卡頁。
- **一個月報指令**：`computai recap` 自動找支援的本機用量，預設最近一個有紀錄且已結束的月份，開啟下載頁。
  可在頁面選月份、年度或累計；`computai recap 2026-09` 可指定月份。
- **本機製卡頁**：選範圍、版型、深淺色與顯示名稱，下載 PNG／SVG、複製貼文文字或匯出目前區間的彙總 JSON。
  沿用 Web／TUI 的風格，支援直式、方形、橫式與 README 圖片；沒有用量時停用下載，避免產生假的零用量月報。
- **月報、年報與個人歷史**：顯示來源、涵蓋日期、紀錄筆數、有用量天數、模型比例及相鄰曆月比較；缺少的紀錄顯示未知。
- **圖卡版型**：新增 Minimal、Paper、GitHub、Terminal，並保留原有 HUD 配色。可用 `--card --html styles.html` 比較風格。
- **Token 細項與本地紀錄**：`--tokens` 說明快取與推理，`--local-history` 看已記錄的推論，
  `--local-requests` 看新版 proxy 的耗時、HTTP 結果與速度；可標記 test／production／benchmark。
- **修正與延續**：保留 beta.2 的跨裝置匿名 session 分組及升級補填；機器斷線不重複計數，SSH 驗證逾時保留修正提示。

## 安裝或升級

需要 Python 3.8+。macOS／Linux：

```sh
curl -fsSL https://raw.githubusercontent.com/Sean-Hawks/computai/v0.1.0-beta.3/install.sh | sh
computai --version       # computai 0.1.0-beta.3
computai                 # 功能選單
```

若找不到指令，將 `~/.local/bin` 加入 PATH。需要繁中介面可執行 `computai --lang zh`。
只想製作月報，可在安裝後執行 `computai recap`，或直接一行完成：

```sh
curl -fsSL https://raw.githubusercontent.com/Sean-Hawks/computai/v0.1.0-beta.3/install.sh | sh -s -- --recap
```

Windows：下載並解壓 `computai-v0.1.0-beta.3.zip`，在該資料夾執行：

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

重新開啟終端機後執行 `computai`。只要月報，可雙擊 ZIP 裡的 `Make a card.cmd`；macOS 對應 `Make a card.command`。
快捷入口仍需要已安裝 Python，不是內建 Python 的桌面應用程式。

安裝器保留既有設定及帳本；執行中的 TUI／Web／watch／proxy 要重新啟動才會載入新程式。
ZIP 附兩種安裝器、製卡快捷入口、說明與授權；Release 附 `SHA256SUMS`。

## 行為變更

- 裸指令在互動終端機顯示選單；非互動環境只印功能指南並結束，**不再等於摘要**。
  腳本請明確使用 `computai --summary` 或 `computai --json`。
- 原有 `--live`、`--web`、`--summary` 等直接指令仍可用。從選單進監控不會先問訂閱方案，可稍後到設定填寫。
- `computai recap` 是月報入口；舊的 `computai --recap YEAR` 仍是年度回顧。
- 選單的網頁選項會自動開瀏覽器，服務只聽 `127.0.0.1`；終端機保持執行，Ctrl-C 停止。

## 隱私與數字

只取用量欄位，不儲存或傳送 prompt、回應內容、登入憑證。選單出現前不讀用量、不連線機器、不建立帳本。
月報與製卡在本機執行，不需要註冊帳號或上傳紀錄；分享用 PNG／SVG 或彙總 JSON。
製卡 HTML 包含可切換的歷史彙總，建議保留在本機。

`B` 是十億 token，包含反覆讀入的快取；推理已包含於輸出，不能再加一次。這是處理量，不等於寫出的文字量。
API 等值是依設定價格估算的用量價值，不是訂閱帳單或已省下的現金。

## 已知限制

- GUI 使用量依支援的本機紀錄取得，不能補回未記錄、已刪除或只有網頁版 LLM 的歷史。
- 本地 token 依服務 metrics 或 proxy 記錄；舊紀錄不能補回逐筆耗時、結果或任務內容。
- 本月及不完整歷史會明示範圍，沒有資料不當成零；年度報告只代表可見紀錄。
- Windows 原生執行、真實 GUI 點擊與 PNG 下載未在本次實機驗收；自動測試使用合成資料與 DOM harness。
- 本次沒有新增模型推論負載，也沒有用真實雲端帳號重新驗證。時間軸與 agent 時數仍是依紀錄推估的活動時間。

測試與 review 見[驗證紀錄](https://github.com/Sean-Hawks/computai/blob/v0.1.0-beta.3/docs/BETA-3-VALIDATION.md)。
更多操作見[繁中手冊](https://github.com/Sean-Hawks/computai/blob/v0.1.0-beta.3/docs/MANUAL.zh-TW.md)
與[第一份月報指南](https://github.com/Sean-Hawks/computai/blob/v0.1.0-beta.3/docs/MAKE-A-CARD.zh-TW.md)。

問題請回報到 [GitHub issues](https://github.com/Sean-Hawks/computai/issues)，附版本、系統、重現指令及 `computai --doctor --redact` 輸出。
