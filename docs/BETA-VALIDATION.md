# v0.1.0-beta.1 驗證紀錄

日期：2026-10-04。範圍：`21c0d04` 之後的公測功能與發佈前修正。

## Code／security review

本次由開發 agent 自行 review，不是外部獨立安全稽核。重點包括：

- 新來源 parser、OpenCode SQLite／WAL、fixture 與去重規則。
- 多裝置匯出的欄位白名單、壞檔保留舊資料、SSH 命令與檔案寫入。
- Hook 放行規則、工具選擇印出的 shell 引號、小隊 JSON 型別與發佈確認。
- 網頁 Host 檢查、DOM escaping、Tailscale 埠選擇與清理。
- 過時狀態、proxy／取樣記帳來源、版本比較與安裝器。

確認並修正：OpenCode 複製含對話內容的資料庫、CLI 時間軸破壞 ANSI、舊取樣誤標活動、
Tailscale 設定讀不到仍繼續、錯誤型別小隊／MCP 輸入、原生 Ollama 取樣導致 proxy 漏帳、
Docker 測試管線掩蓋失敗與測試 log 相互覆寫。

程式沒有新增第三方套件、沒有 shell=True／eval；動態 hook exec 只執行程式內的固定邏輯。
本次不存取登入憑證，不加入真實對話、帳本、設定、金鑰或本機交接紀錄至發佈檔案。

## 自動測試

```sh
sh tests/run.sh
sh tests/docker.sh
```

300 個測試：macOS Python 3.14.6／3.8.20 通過；Linux `python:3.8-slim` 與 `ubuntu:24.04` 通過。
Linux 會略過缺少 macOS 工具或字型等平台相關測試；fixture 測試不代表真實雲端帳號已驗證。
Docker runner 另外用假測試退出碼驗證：失敗會讓整個腳本回傳非零。

## 實機與畫面

- `tests/e2e_ollama.py --requests 4`：獨立隨機埠的 Ollama／proxy，原生 generate、chat、OpenAI 串流／非串流。
  測試腳本與帳本均為 4 個請求、58 個輸入 token、96 個輸出 token；閒置模型警示與耗電積分正常。測試後已清理自己啟動的服務。
- Timeline：真實用量唯讀預覽、145×47 終端與 TUI；另測英／繁中、60～160 欄、多種高度及 ANSI 注入防護。
- Tailscale：先前已驗證 tailnet 的 `/`、`/healthz` 回 HTTP 200，結束後既有設定保留；此次新增設定讀取失敗時不更動服務的回歸測試。
- 安裝：本機 checkout 與 Linux 乾淨 HOME、固定版本下載路徑、含空白的安裝位置。

## 仍待實機驗證

Windows、真實 Cursor CSV、真實雲端供應商帳號、兩台電腦的共用資料夾同步、手機加入主畫面。
模型成本是價格／耗電估計，並未驗證模型品質相等或現金節省。
這些限制已放進 release notes，供朋友按自己使用的環境回報。
