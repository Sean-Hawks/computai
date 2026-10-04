# ComputAI v0.1.0-beta.2

修正 [issue #3](https://github.com/Sean-Hawks/computai/issues/3)：跨裝置匯入的用量現在保留匿名 session 分組，讓時間軸、PEAK PARALLEL、LONGEST RUN 和 AGENT HOURS 能分開計算各個 session。

## 修正內容

- 只交換原始 session ID 的單向雜湊，依裝置與來源區分；原始 ID、prompt、回應及完整專案路徑不外流。
- 新舊匯出格式相容，無效 session 雜湊會整份拒絕並保留上一份好的資料。
- 同一裝置已匯入的舊紀錄可補回缺少的匿名 session，不重複計費、不降低較完整的 token 數，不覆蓋本機或既有 session。
- 共用資料夾在升級後重寫完整匯出，即使用量沒有增加。
- SSH 升級後成功拉取一次完整歷史，再恢復增量；失敗時下次重試。

## 安裝與升級

macOS／Linux：

```sh
curl -fsSL https://raw.githubusercontent.com/Sean-Hawks/computai/v0.1.0-beta.2/install.sh | sh
computai --version       # computai 0.1.0-beta.2
computai --sync
```

Windows：下載並解壓 `computai-v0.1.0-beta.2.zip`，在解壓後的資料夾執行：

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
computai --version
computai --sync
```

- **共用資料夾**：兩端都更新，再各執行一次 `computai --sync`。
- **SSH 拉取**：更新拉取端，執行 `computai --sync`；遠端的快取執行檔會自動更新。
- 已執行中的 TUI／Web 需重新啟動才會載入新程式。
- Release 附程式、macOS／Linux 和 Windows 安裝器、ZIP 與 `SHA256SUMS`。既有設定和帳本會保留。

## 驗證與限制

- 307 個測試於 macOS Python 3.14／3.8、Linux Python 3.8 與 Ubuntu 24.04 通過；Linux 有 14 個平台測試略過。[驗證紀錄](https://github.com/Sean-Hawks/computai/blob/v0.1.0-beta.2/docs/BETA-2-VALIDATION.md)。
- 合成資料回歸涵蓋匿名分組、新舊相容、無效雜湊、舊資料補填與升級重拉。
- 兩個重疊的遠端 session 匯入後仍為兩列、同時數 2、最長連續 240 秒，與原始分組一致。
- 原始 log 沒有 session、來源端仍是舊版，或 log 已刪除時，缺少的歷史分組無法補回。
- Windows、真實雲端同步資料夾及回報者機器未在本次實機驗證；SSH 流程以本機隔離環境驗證。
- 時間軸與 agent 時數仍依請求間隔推估，屬用量統計，並非精確執行計時。

其他功能與使用方式見[繁中手冊](https://github.com/Sean-Hawks/computai/blob/v0.1.0-beta.2/docs/MANUAL.zh-TW.md)及[多裝置說明](https://github.com/Sean-Hawks/computai/blob/v0.1.0-beta.2/docs/MULTI-DEVICE.md)。

感謝 issue #3 與參考 [PR #4](https://github.com/Sean-Hawks/computai/pull/4) 的回報與驗證資訊。
