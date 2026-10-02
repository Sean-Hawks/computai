# NIGHT_LOG

每個里程碑做完在這裡補一段交接。最新的在最下面。

## 分支的做法

每個里程碑一個分支（`m1-skeleton`、`m2-subscriptions`……），做完在本機 fast-forward 合進 `main`，
下一個里程碑從 `main` 開。全部都沒有 push。

## M1 骨架（分支 `m1-skeleton`）

**做了什麼**
- 單一檔案 `computai`（Python 3.8+，只用標準函式庫）。
- 設定檔目錄 `~/.config/computai/`（`COMPUTAI_CONFIG_DIR`、`XDG_CONFIG_HOME`，Windows 用 `%APPDATA%`）：
  第一次執行時寫入 `config.ini`（方案月費）和 `prices.ini`（API 價目表）；之後只讀檔案，使用者改的會保留。
- 金鑰只從環境變數或權限 600 的 `secrets.ini` 讀；權限太寬會警告並忽略。
- 帳本 `~/.local/share/computai/ledger.sqlite`（`COMPUTAI_DATA_DIR`、`XDG_DATA_HOME`，Windows 用
  `%LOCALAPPDATA%`）。`usage` 以 `(source, uid)` 當主鍵，`INSERT OR IGNORE`，所以重複匯入不會重複計算。
  `files` 表記錄每個 log 檔的大小和修改時間，沒變的檔案不會重讀。
- 指令：`--sync`、`--summary`、`--month [YYYY-MM]`、`--since`、`--until`、`--json`、`--paths`、`--no-sync`。
  `--summary` 預設會先自動同步一次。
- 花費在查詢時才用價目表換算，所以改價格會立刻反映到舊資料。
- 測試：`tests/run.sh` 會用 python3 和 Python 3.8（uv 裝的）各跑一次。

**替你做的決定**
- 設定檔用 INI（`configparser`）：3.8 沒有 `tomllib`，JSON 又不能寫註解。
- token 欄位統一成 Anthropic 的語意：`input` 是「沒命中快取的輸入」，OpenAI 的資料匯入時先扣掉 cached。
  `output` 含 reasoning，`reasoning` 只是細項。
- 非整月的範圍，方案月費按天數比例攤（30.44 天一個月）。

**還沒實機驗證**
- Windows 路徑（`%APPDATA%`、`%LOCALAPPDATA%`）只有程式邏輯，沒在 Windows 上跑過。

## M2 訂閱用量（分支 `m2-subscriptions`）

**做了什麼**
- Claude Code：讀 `CLAUDE_CONFIG_DIR`（可逗號分隔多個）或 `~/.claude`、`~/.config/claude` 底下
  `projects/**/*.jsonl`（含 `subagents/`）。只取 assistant 行的 `message.usage`，用
  `(message.id, requestId)` 去重。**實測發現同一則訊息的重複行 output 會隨串流變大**（例如 8 → 377），
  所以保留 token 最多的那筆；帳本的 upsert 也會用較大的那筆覆蓋舊的半截紀錄。
  快取寫入分 5m／1h；`thinking_tokens` 記在 `reasoning`；`speed: fast` 會記成 `<model>@fast` 另外計價；
  `isSidechain` 或 `subagents/` 路徑記為 subagent；`cwd` 當專案。
- Codex：讀 `CODEX_HOME` 或 `~/.codex` 的 `sessions/` 和 `archived_sessions/`。用量來自
  `event_msg/token_count` 的 `last_token_usage`，累計值沒變的重複事件略過；uid 用「時間＋累計值」，
  fork 出來的 session 複製父 session 的事件時不會重複計算。OpenAI 的 input 匯入時先扣掉 cached。
  `rate_limits` 存進 `limits` 表。
- `--summary` 多了：每個來源的 reasoning 比例、subagent 比例、方案月費比較、額度視窗（使用率和重置倒數，
  已經過了重置時間的當 0%，8 天沒出現的視窗不顯示）。
- `--by project|session|day` 拆分（中文路徑也對得齊；顯示寬度的工具從 slurmtop 84cd35d 移植）。
- 預設價目表（`prices.ini`）照 2026-10-03 的官方價格頁填好，查證紀錄在 `docs/VERIFIED-2026-10-03.md`。

**用這台 Mac 的真實資料驗證的結果**
- Claude Code 2026-09：每個模型的 token 數和花費都跟 `npx ccusage@latest monthly` 完全一樣
  （opus-5 $115.39、opus-5-5 $82.45、fable-5-1 $57.99、opus-4-8 $34.96）。
- 價格：用 Claude Code 自己寫在 log 裡的 `cost-state` 反推單價，opus-5-5 的 1 小時快取寫入正好
  $8/MTok、sonnet-5-5 的 5 分鐘快取寫入正好 $2.5/MTok，跟價目表一致。
- Codex：2026-06 到 2026-10 每個月每個模型的 input／cached／output 都跟 ccusage 一模一樣
  （例如 9 月 gpt-6-astra 25,385,619／541,809,152／2,865,920）。
  183 個 thread 中有 167 個跟 Codex 自己 `state_5.sqlite` 的 `threads.tokens_used` 完全相同；
  不同的是 fork 出來的 thread（檔案裡帶著父 thread 的事件，帳本層級已去重）和一個 thread 分成多個
  rollout 檔的情況。
- **花費跟 ccusage 不同的地方**：gpt-5.6-sol（7 月 $118 vs ccusage $177）和 gpt-6-astra（9 月 $939 vs
  $1,150）。token 一樣，差在單價：我們用的是 OpenAI 官方價格頁（2026-10-03 查），ccusage 的價目表
  看起來是 1.5 倍左右，可能是舊價或長 context 價。你可以在 `prices.ini` 自己改。

**替你做的決定**
- Codex 不用新版的 `token_usage_record`：它的加總比 Codex 自己記的 `tokens_used` 多 2% 左右，
  而 `token_count` 跟 Codex、ccusage 都對得上。
- `codex-auto-review` 這個模型沒有公開價格，先列為「沒有價格」（summary 最後一行會提醒）。
  ccusage 把它當 gpt-5.6-luna 計價，但我找不到官方對應關係。
- Codex log 的 `plan_type` 有 `prolite`、`pro`、`plus` 三種，跟你說的「ChatGPT Pro (20x)」不完全一樣；
  `config.ini` 預設 Claude Max 5x $100、ChatGPT Pro $200，**請確認月費**。
- 額度視窗用長度命名（`5h`、`week`），因為 Codex 現在的 primary 是一週、不是 5 小時。

**還沒驗證／已知限制**
- Claude Code 背景用的 haiku（標題、摘要等）不會寫成 assistant 行，log 裡看不到，所以會少算一點；
  ccusage 也一樣。
- Claude 的額度 % 不在 log 裡，官方來源是 statusline 的 stdin JSON（`rate_limits.five_hour` 等），
  M3 的 `--statusline` 會順便記錄。
- web search 的按次計費（$10／1000 次）還沒算進去。
