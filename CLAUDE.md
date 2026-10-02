# ComputAI

一眼看完你的算力和 AI 花費：Claude、Codex、本地模型、homelab、雲端 GPU，放在同一本帳裡。

## 開始工作前

- 先讀 `GOAL.md`（整體目標和里程碑）、`docs/RESEARCH.md`（已驗證的資料格式、競品、點子），
  以及 `NIGHT_LOG.md`（如果存在，裡面是上一個 session 的交接）。
- 姊妹專案 slurmtop 在 `~/Documents/slurmtop`（MIT 授權，同一個作者）。SSH 讀取節點、GPU 偵測、
  耗電積分、`--web`、`--report` 都可以從那裡移植；搬過來的程式碼要註明來源的 commit。

## 原則

- 單一 Python 檔（`computai`），只用標準函式庫，支援 Python 3.8+；macOS、Linux、Windows 都要能跑。
- 被監控的節點上只需要 SSH 和 POSIX `sh`，不用安裝 agent。唯一可以常駐的是可選的 token 計數 proxy。
- 隱私：讀使用者的 log 時只取用量欄位，絕對不讀、不存、不傳 prompt 和回應的內容。
  不讀 `~/.codex/auth.json` 和 Claude 的 OAuth token。
- 金鑰只從環境變數或權限 600 的設定檔讀，不能出現在 log、`--json`、`/metrics` 或錯誤訊息裡。
  不要把任何金鑰、`.env`、`.dev.vars` 加進 git。
- 價格、電價、方案費用全部放在可以編輯的設定檔，附上查價日期，程式裡不寫死。
- 每個資料來源都要有 fixture 測試（`tests/fixtures/`）；用真實資料做 fixture 前，先把文字內容換成假資料。
- 網頁和 proxy 預設只聽 `127.0.0.1`。

## 工作方式

- 用繁體中文和使用者溝通。
- 每個里程碑開一個分支，做完在 `NIGHT_LOG.md` 補交接：做了什麼、替使用者做的決定、還沒實機驗證的部分、
  建議下一步。
- **小步、頻繁地 commit**：每完成一個小單位就 commit 一次，不要累積成一個大 commit。小單位例如：
  一個 parser、一組 fixture、一個測試、一個指令選項、一段文件、一個 bug fix、一次重構。
  每個 commit 只做一件事，訊息用英文祈使句講清楚做了什麼（例如 `Parse Codex token_usage_record lines`）。
  commit 前跑相關的測試，確保每個 commit 都是可以執行的狀態；不要為了增加數量而做空的或沒有意義的 commit。
- 沒有使用者同意，不要 push、不要開 PR、不要發佈版本。
