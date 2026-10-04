# Goal：把算力與 AI 花費放在同一本可信的帳裡

> **ComputAI** — where your compute and AI money goes.
> 一眼看完你的算力和 AI 花費：Claude、Codex、本地模型、homelab、雲端 GPU，放在同一本帳裡。

開始前先讀 `CLAUDE.md`（原則）和 `docs/RESEARCH.md`（已驗證的資料格式、競品、點子）。

## 要解決的問題

一個人同時有 homelab 機器、上面跑的本地小模型、租的雲端 GPU，還有 Claude 和 ChatGPT 訂閱，
卻沒有一個地方可以回答：**我總共用了多少算力和 AI、花了多少錢、哪裡在浪費、該怎麼調整？**
現有工具各只做一塊（ccusage／CodexBar 只看訂閱，各種 llmtop 只看本地推論），沒有人把四塊放在同一本帳。

## 目前階段：收斂與驗證（2026-10-04）

已有 beta.3 主線；接下來優先回答三個問題：**用了多少、花了多少、哪裡浪費。**
依 [目前路線圖](docs/ROADMAP.md) 一次完成一個小單位，把已做的能力變得可信、好懂、容易維護。

- **持續改善核心**：用量匯入與去重、多裝置帳本、花費與額度、算力與本地模型、浪費警示。
- **收斂介面**：TUI、Web、狀態列、報告共用彙總與判斷，明確標示資料來源、涵蓋範圍和更新時間。
- **暫緩周邊擴充**：保留製卡、排行榜、MCP、選工具、hook 等既有能力與相容性；先修問題，
  暫停新增卡片風格、成就、排行榜玩法及自動執行操作。
- **先完成驗證**：區分 fixture／自動測試通過與實機驗收；缺價格、缺用量、過時資料與預估值都要可辨認。
  API 等值不是額外帳單，已知支出也不代表完整實付金額。

新增功能前，先說清楚它回答哪個核心問題、現有能力缺在哪裡，以及需要負擔哪些資料來源、
介面、相容性與驗證工作。能用既有選項或共用函式解決，就優先沿用。
已授權且完成的分支先評估、驗收，再逐步整合；不因收斂直接刪功能、分支或使用者資料。
維持單一 Python 檔、標準函式庫與 Python 3.8+，用小步整理減少重複，不先做大型重構。

## 四類資料，統一換算成 token、GPU 小時、kWh 和錢

| 類別 | 來源 |
|---|---|
| A. Homelab 機器 | 從 slurmtop 移植的 SSH 讀取：GPU、CPU、功耗，換算成電費 |
| B. 本地模型 | Ollama、llama.cpp、vLLM、SGLang、LM Studio、MLX；Ollama 的 token 數靠可選的 proxy |
| C. 雲端 GPU | RunPod、Vast.ai、Lambda 的 API，加上 SSH 讀實際使用率 |
| D. AI 訂閱與 API | Claude Code 和 Codex 的本機 log（token、額度 %）、Anthropic 和 OpenAI 的 usage/cost API |

## 第一版里程碑（歷史規劃）

以下保留初版範圍與驗收條件；不是目前待辦清單，也不表示每個平台與資料來源都已實機驗收。
後續優先順序以上方「目前階段」與路線圖為準。

每個里程碑都拆成很多個小 commit，一個 parser、一組 fixture、一個選項就 commit 一次，不要一次 commit 一整個里程碑。

1. **骨架**：單一檔案 `computai`、設定檔（`~/.config/computai/`）、sqlite 帳本（`~/.local/share/computai/`，
   Windows 用 `%LOCALAPPDATA%`）。匯入要冪等，同一筆資料匯入兩次不能重複計算。
   指令：`--sync`、`--summary [--since/--month]`、`--json`。
2. **D：訂閱用量**：Claude Code 和 Codex 的 log 解析，包含去重、cache 和 reasoning 分開記錄、
   專案歸屬、等值 API 花費和月費的比較、Codex 額度 % 與重置倒數。用使用者這台 Mac 的真實資料驗證，
   並跟 `npx ccusage` 的數字對照。
3. **一行顯示**：`computai --line` 輸出「Claude 42%｜Codex 100%｜今日 $3.2」這種一行文字，並附上
   Claude Code statusline、tmux、SwiftBar 的設定範例。
4. **B 和 A：本地模型與機器**：偵測推論服務、讀取 metrics、閒置佔卡警示；可選的 `--proxy` 用來統計
   Ollama 和 OpenAI 相容 API 的 token；每台機器的 AI 使用佔比、kWh、電費、J/token。
   在這台 Mac 上用 ollama 加 `qwen3:0.6b` 實測（模型已經下載好，測完要關掉服務）。
5. **C：雲端 GPU**：先做 RunPod、Vast、Lambda，只呼叫唯讀 API。最重要的警示是「閒置但還在計費」。
6. **分析**：快取效率（哪些 session 一直在重寫快取、浪費多少錢）、GPU 回本計算機、方案模擬器、
   月底花費預測、台灣時間電價。
7. **總帳畫面**：終端機 live 畫面分「算力／AI 用量／警示」三區；`--web` 要有手機版排版；`/metrics`；
   月報可以輸出 `--html`。安裝腳本（`install.sh`、`install.ps1`）、README（英文和繁中）、使用手冊。

初版規劃曾延後以下項目（部分後來已實作，現在保留相容性並暫緩擴充）：MCP server、Discord 和 Telegram 週報、實驗室彙總模式、
核銷匯出、年度回顧卡、智慧插座、Wake-on-LAN、「現在能跑哪些模型」。

## 第一版完成的定義（歷史驗收條件）

- 在這台 Mac 上執行 `computai --summary --month`，看得到真實的 Claude Code 和 Codex 用量與等值花費，
  數字跟 ccusage 和 Codex 自己的紀錄對得上。
- 本地 ollama 的模擬 homelab 端對端測試通過：proxy 記錄的 token 數和測試腳本統計的一致，閒置警示會出現。
- 雲端和 API 的部分有 fixture 測試；沒有實機驗證的部分要在 NIGHT_LOG 清楚標示。
- 全部測試通過；最後跑一次 code review 和 security review，確認的問題都修掉。
- 沒有 push、沒有發佈，停下來讓使用者驗收。
