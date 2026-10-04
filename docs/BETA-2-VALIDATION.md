# v0.1.0-beta.2 驗證紀錄

日期：2026-10-04。以公開 beta.1 為基礎，只加入 issue #3 的匿名 session 修正、升級重播與發佈版本調整。

## 自動測試

- 307 個測試於 macOS Python 3.14.6／3.8.20 通過。
- Linux `python:3.8-slim` 全套通過，14 個平台相關測試略過。
- Ubuntu 24.04 第一輪遇到 proxy 測試的非同步記帳競態；回應已送出但 SQLite 尚未完成 commit。
  測試改為最多等待兩秒後比對完整三筆用量，保留缺筆／錯誤 token 的失敗條件；沒有修改 proxy 執行行為。
- 調整後 proxy 14 個測試於 macOS Python 3.14／3.8 通過，Ubuntu 24.04 全套重新驗證通過。
- Python 3.8 語法、安裝腳本語法、發佈文件本機連結與 `git diff --check` 通過。

## 相容性與隱私 review

由開發 agent 自行 review，檢查匯出白名單、匿名 hash 格式、補填的裝置邊界、增量游標及舊格式相容性。

- 原始 session ID 不出現在交換檔或接收帳本；雜湊依裝置／來源隔離。
- 同裝置既有空 session 可補填；不覆蓋本機、異裝置或已有 session，也不降低 token 數與 requests。
- 直接載入 beta.1 parser 確認能讀新匯出，新增欄位會略過。
- 共用資料夾因格式升級而重寫完整匯出；SSH 成功全量拉取後才標記升級完成，失敗保留重試。
- 兩個重疊遠端 session 的時間軸與圖卡指標回歸通過。

Release assets 只包含已提交的程式、安裝器、公開說明及授權，不包含本機 NIGHT_LOG、設定、憑證、帳本或對話 log。

## 實機限制

本次未在 Windows、回報者機器或真實雲端同步資料夾驗證；SSH 使用本機 sh 與合成資料驗證。
沒有重新執行 Ollama 模型負載，proxy runtime 與其他資料來源未改動；沿用 beta.1 的實機驗證紀錄。
