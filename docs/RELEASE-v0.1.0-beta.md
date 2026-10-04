# ComputAI v0.1.0-beta（草稿，等作者確認後才發佈）

> **一眼看完你的算力和 AI 花費。** Claude、ChatGPT 訂閱、本地模型、homelab 機器和租用的雲端 GPU，
> 放在同一本帳裡。

這是 ComputAI 的第一個公開測試版。整個程式只有一個 Python 檔案，支援 Python 3.8 以上，
只用標準函式庫，可在 macOS、Linux 和 Windows 執行。被監控的機器只需要 SSH 和 `sh`。

## 安裝

```sh
curl -fsSL https://raw.githubusercontent.com/Sean-Hawks/computai/main/install.sh | sh
computai            # 即時總帳畫面；第一次執行會詢問你的訂閱方案
computai --doctor   # 偵測到什麼、缺什麼，以及每一項要下的指令
```

Windows：`powershell -ExecutionPolicy Bypass -File install.ps1`。

## 能做什麼

- **訂閱用量**：從 Claude Code 和 Codex 的 log 統計各模型、各專案的 token，快取與推理用量分開顯示，
  並把照 API 價格換算的等值花費和訂閱月費比較。整個帳號的額度由官方 `claude`、`codex` 指令查詢，
  不讀取登入憑證、不消耗額度。查詢頻率跟著消耗速度調整：平常每 10 分鐘一次，消耗快時最短每分鐘一次，
  重置後 30 秒再查一次。
- **本地模型**：支援 Ollama、llama.cpp、vLLM、SGLang、LM Studio；可選的 `--proxy` 統計 Ollama 的 token，
  並提醒「模型已載入卻沒在用」。
- **機器監控**：透過 SSH 讀取 CPU、GPU、功耗、度數與電費；提供台電時間電價預設值，也支援智慧插座。
- **雲端 GPU**：支援 RunPod、Vast.ai、Lambda，只呼叫唯讀 API，提醒「閒著卻還在計費」的 GPU。
- **分析**：快取效率、月底花費預測與預算、方案模擬器、GPU 回本計算機。
- **呈現與整合**：終端機總帳畫面、`--web` 網頁版（含手機排版）、`/metrics`、`--html` 報告、
  Claude Code／tmux／SwiftBar 一行狀態列、`--wrapped` 回顧、GitHub 個人頁卡片，以及 MCP server。

## 這次公測新增

- **首次執行引導**：沒有資料的地方會說明去哪裡找過 log、怎麼接上額度；每個訂閱只問一個方案問題，
  並先根據 log 推測方案供你確認。
- **適合回報問題的診斷**：`computai --doctor --redact` 會將機器名稱、主機位址、IP、專案名稱和家目錄路徑
  換成代號。
- **更新檢查**：每天最多一次，可用 `[general] update_check = no` 關閉。只讀取 GitHub 上 `computai` 的版本行，
  不傳送你的個人資料或用量。
- **多台電腦的用量合併**：透過共用資料夾（iCloud、Dropbox、Syncthing）或 SSH 拉取，只交換用量數字，
  詳見[多裝置設定](MULTI-DEVICE.md)。
- **自適應額度查詢**：查詢頻率跟著消耗速度調整（`[limits] refresh = adaptive|fixed`）；`--doctor` 會顯示
  下次查詢時間和原因。

## 隱私

只取用 log 裡的用量欄位，不儲存、不傳送提示詞與回應內容。不讀取 `~/.codex/auth.json` 或 Claude 的 OAuth token。
網頁伺服器和 proxy 預設只監聽 `127.0.0.1`。

## 已知限制

- Windows 的測試覆蓋較 macOS、Linux 少。
- 無法從本機資料直接讀出 Claude 的訂閱方案，首次執行時會先推測，再請你確認。

遇到問題時，請開一則 issue，附上 `computai --doctor --redact` 的輸出。
