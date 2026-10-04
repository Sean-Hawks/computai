# ComputAI v0.1.0-beta.1

**一眼看完你的算力和 AI 花費。** Claude、Codex、本地模型、homelab 與雲端 GPU，放在同一本帳裡。

這是第一個供朋友試用的 beta。程式只有一個 Python 檔，只用標準函式庫，需要 Python 3.8 以上。

## 安裝固定版本

macOS／Linux：

```sh
curl -fsSL https://raw.githubusercontent.com/Sean-Hawks/computai/v0.1.0-beta.1/install.sh | sh
computai --version       # computai 0.1.0-beta.1
computai --lang zh       # 即時總帳；第一次會詢問訂閱方案
computai --doctor --redact
```

若找不到指令，將 `~/.local/bin` 加入 PATH。也可以下載 release 的 `computai-v0.1.0-beta.1.zip`，解壓後執行 `sh install.sh`。

Windows：下載並解壓同一份 ZIP，於資料夾內執行：

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

重新開啟終端機後執行 `computai --version`。Release 附有 `SHA256SUMS`；ZIP 包含程式、兩個安裝腳本和繁中試用說明。

## 可以試什麼

- **訂閱與其他工具用量**：Claude Code、Codex、Gemini CLI、OpenCode，以及手動匯入 Cursor 用量 CSV。
  可看各模型／專案的 token、快取、推理用量、API 等值與訂閱月費。Claude／Codex 額度透過官方 CLI 查詢，查詢間隔跟著消耗速度調整。
- **本地推論與機器**：Ollama、llama.cpp、vLLM、SGLang、LM Studio；可選的 token proxy；SSH 讀取 GPU、CPU、功耗與電費。
- **雲端與成本分析**：RunPod、Vast.ai、Lambda 唯讀查詢、閒置計費警示、預算與月底預測、方案與本地模型成本比較。
- **總帳與時間軸**：TUI 六個分頁、手機網頁、SVG 時間軸、HTML 報告、Wrapped、GitHub 個人頁卡片。
  時間軸明示起迄時間、累計活動與 token，Claude/Codex 時數與本地推論分開顯示。
- **多裝置與整合**：共用資料夾／SSH 合併 Claude、Codex 用量、Tailscale 網頁存取、`--pick` 工具建議、可選額度 hook、小隊總數排行榜、MCP、Prometheus。

```sh
computai --summary --month --lang zh
computai --timeline --lang zh
computai --pick
computai --local-cost --lang zh
computai --web --tailscale --lang zh     # 已安裝並登入 Tailscale 才使用
```

細節見[繁中手冊](https://github.com/Sean-Hawks/computai/blob/v0.1.0-beta.1/docs/MANUAL.zh-TW.md)、[多裝置設定](https://github.com/Sean-Hawks/computai/blob/v0.1.0-beta.1/docs/MULTI-DEVICE.md)。

## 這次發佈前的修正

- 修正只監控原生 Ollama 時 proxy 停止逐筆記帳的漏帳；實機四種請求的 token 與帳本一致。
- 過時的機器取樣標成「太久沒回報」，不再沿用舊的推論狀態、即時速度與功耗。
- OpenCode 用唯讀交易讀取用量與 WAL，不複製含對話內容的資料庫、不查詢 `part` 表。
- 修正時間軸 ANSI 色碼殘留與可讀性；新增時間刻度、圖例及每列時間／token 欄位。
- Tailscale 設定讀不到時停止，保留既有服務；可用埠會避開其他服務。
- 外部小隊資料與非物件 MCP 輸入不再使讀取程序中斷。
- 安裝器固定 beta 版本，更新比較支援 beta 序號；Docker 測試保留真實失敗退出碼。

## 隱私與數字的意思

只取用量欄位，不儲存、不傳送 prompt 與回應內容；不讀取 `~/.codex/auth.json` 或 Claude OAuth token。
網頁與 proxy 預設只監聽 `127.0.0.1`。API 等值不是訂閱實際帳單，本地成本比較也不代表一定省下同額現金或具有相同模型品質。

## 已知限制

- Windows 尚未實機驗證。雲端供應商與 Cursor 的資料解析有 fixture 測試，真實帳號／匯出仍待朋友驗證。
- 手機加入主畫面、兩台真實電腦的共用資料夾合併，尚未完整實機驗收。
- 不一定能從 log 判定訂閱方案，首次執行會推測再詢問；官方 CLI 版本變更可能影響額度查詢。
- 舊 `prices.ini` 不會被安裝器覆寫；`--doctor` 會提示缺價格的模型，需自行補上有查價日期的價格。
- 本地 token 完整度取決於是否經過 proxy／服務是否提供 metrics；無法從用量帳本還原任務內容。
- 時間軸依請求間隔推估活動，各列時數相加；不是精確執行時間。

## 回報問題

先確認安裝與第一次執行是否順利、數字是否看得懂，以及你使用的來源是否有被記錄。
請在 [GitHub issues](https://github.com/Sean-Hawks/computai/issues) 附上版本、作業系統、重現指令與 `computai --doctor --redact` 的輸出。
請勿附上登入憑證或原始對話 log。
