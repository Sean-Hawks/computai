# ComputAI 調查筆記（2026-10-02～03）

## 已經在使用者的 Mac 上驗證的資料格式

- **Claude Code log**：`~/.claude/projects/<專案>/<session>.jsonl`（位置可以用 `CLAUDE_CONFIG_DIR` 改）。
  - `type: "assistant"` 那一行的 `message.usage` 有 `input_tokens`、`cache_creation_input_tokens`、
    `cache_read_input_tokens`、`output_tokens`、`output_tokens_details.thinking_tokens`、`server_tool_use`。
    cache 寫入另外分成 `cache_creation.ephemeral_5m_input_tokens` 和 `ephemeral_1h_input_tokens`。
  - 同一行也有 `message.model`、`message.id`、`requestId`、`timestamp`、`isSidechain`（subagent）和 `cwd`。
  - **同一則訊息可能出現在好幾行**，要用 `(message.id, requestId)` 去重。
  - Anthropic 的 `input_tokens` **不含** cache 的部分。
  - 這台 Mac 上大約有 200 個 session 檔。
- **Codex log**：`~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`，另外還有 `~/.codex/archived_sessions/`
  （位置可以用 `CODEX_HOME` 改）。
  - `type: "token_usage_record"`：每個 response 一筆，用 `response_id` 去重。
    `usage` 有 `input_tokens`、`cached_input_tokens`、`cache_write_input_tokens`、`output_tokens`、
    `reasoning_output_tokens`、`total_tokens`。
  - OpenAI 的 `input_tokens` **已經包含** cached 的部分，跟 Anthropic 相反。
  - `event_msg` 裡 `payload.type: "token_count"` 那筆有累計用量和 `rate_limits`：
    `primary` 和 `secondary` 各有 `used_percent`、`window_minutes`、`resets_at`（epoch），
    另外有 `credits.balance`。
  - 模型名稱在 `turn_context.payload.model`；`session_meta.payload.originator` 記錄是哪個前端開的。
  - `~/.codex/` 底下還有好幾個 sqlite（`state_5.sqlite` 等），可能有彙總資料。只能唯讀，
    而且 Codex 正在執行時也要能安全讀取。
- **Ollama 0.17.5**：
  - **沒有 `/metrics`**（回 404）。
  - `/api/ps` 只列出已載入的模型（`size`、`size_vram`、`expires_at`、`context_length`、
    `details.quantization_level`）。
  - token 數只出現在每次生成的回應裡（`prompt_eval_count`、`eval_count` 和各段 duration）。
  - server log 只有 `[GIN]` 請求行，沒有 token 數。
  - 所以要統計 Ollama 的 token，只能靠轉發 proxy。
- **這台 Mac 的環境**：已經裝了 `ollama`，也下載了 `qwen3:0.6b`（約 1 GB）；沒有 llama.cpp 和 LM Studio，
  需要的話可以用 brew 裝 llama.cpp。
- **使用者的方案**：Claude Max 5x、ChatGPT Pro（20x）。目前沒有在跑的 homelab，也沒有雲端 GPU 帳號。

- **Gemini CLI**（2026-10-04 在這台 Mac 核對）：`~/.gemini/tmp/<專案>/chats/*.jsonl`，`.project_root` 是專案路徑。
  `type: "gemini"` 的行有 `tokens: {input, output, cached, thoughts, tool, total}`，同一個 id 會重寫好幾次。
  273 筆全部 total = input + output + thoughts + tool → input 含 cached、output 不含 thoughts。subagent 在 `chats/<主 session id>/`。
- **OpenCode**（2026-10-04）：`~/.local/share/opencode/opencode.db`（sqlite，WAL）。`message.data` 的 assistant 訊息有
  `tokens: {input, output, reasoning, cache: {read, write}}`、`modelID`、`time.created`（毫秒）、`path.cwd`、`cost`；
  依 anomalyco/opencode `session.ts` 的 getUsage，這五個數字互不重疊。對話文字在 `part` 表。
- **Cursor**：沒有本機 log。帳號頁的用量 CSV 標題（第三方 lukedeaves/cursor-ai-usage-dashboard）：
  `Date,Kind,Model,Max Mode,Input (w/ Cache Write),Input (w/o Cache Write),Cache Read,Output Tokens,Total Tokens,Cost`，未用真檔核對。
- **Codex hooks**（learn.chatgpt.com/docs/hooks）：`~/.codex/hooks.json` 或 config.toml 的 `[[hooks.PreToolUse]]`，格式跟 Claude Code 相容；
  新 hook 要在 codex 裡 `/hooks` 信任一次；派 subagent 的工具是 `spawn_agent`。
- **台灣電力排碳係數**：113 年度 0.474 kg CO2e/度（經濟部能源署 2025-04-14 公布）。

還沒查證、實作前要先看官方文件的項目：
- Claude Code 額度百分比的官方來源（statusline 的輸入 JSON？`/usage`？）
- 各平台現在的 API 價格
- RunPod、Vast、Lambda 的 API
- Anthropic 和 OpenAI 的 admin usage/cost API
- LM Studio、MLX 的 metrics

## 競品（2026-10 調查）

| 類別 | 代表專案 | 狀況 |
|---|---|---|
| 訂閱用量 | CodexBar（22k 星，macOS 選單列）、ccusage（18.8k 星）、Claude-Code-Usage-Monitor（8.7k 星）、tokscale（5.6k 星）、tokentop（74 星） | 成熟而且擁擠，只看訂閱 |
| 本地推論 | InfraWhisperer/llmtop（Go，vLLM、SGLang、Kubernetes）、ProgrammerPeasant/llmtop（Rust，只支援 Ollama，有 J/token 和電費）、rxxusp/llmtop 等十幾個同名專案 | 幾乎都只有終端機畫面，不碰雲端和訂閱 |
| 硬體監控 | nvtop、bottom、gpustat、macmon、all-smi | 成熟，但不管 LLM 和錢 |
| 雲端 GPU | 只有幾個不到 5 星的單一平台閒置腳本 | 幾乎是空白 |
| 跨類別 | jamesbrink/burnrate（2 星，macOS 選單列：Claude Code、Codex、OpenRouter、RunPod、AWS） | 最像我們，但沒有本地 GPU、電費和本地模型 |
| API 代理型 | LiteLLM、Langfuse、Helicone | 流量要經過它們才記得到，不讀本機 log，也沒有 GPU 資料 |

**差異點**：
- 四類資料放在同一本帳。
- 用實際 GPU 使用率判斷「雲端閒置還在計費」。
- 本地模型和雲端的每 token 成本比較。
- 台灣在地功能：時間電價、核銷匯出。

## 名稱

定案為 **ComputAI**（指令、repo 和套件名稱都用 `computai`）。

- PyPI、npm、Homebrew 都沒有人用；GitHub 上只有一個不相干、1 星的作品集 repo。
- 網域：`computai.com` 已經被註冊；`computai.ai` 查不到註冊紀錄，看起來還能買。
- 名字本身看不出是統計工具，所以一定要搭配副標題：*where your compute and AI money goes*。

## 點子清單（研究候選，非目前待辦）

2026-10-04 起，以 [目前路線圖](ROADMAP.md) 的收斂與驗證順序為準。
以下保留調查時的點子；已有實作與未實作項目混列，不代表應繼續擴充。
新來源、分享風格、成就與整合先提出具體使用缺口，再評估維護與驗證成本。

**當時的優先候選**：
- 一行顯示（statusline、tmux、SwiftBar）
- 雲端閒置計費警示
- GPU 回本計算機與方案模擬器
- 快取效率分析
- 年度回顧卡

**花錢決策**：
- 雲端比價：同樣的 GPU 在別的平台現在多少錢
- 台電時間電價：建議把批次工作排到離峰時段
- 月底花費預測與預算警示

**額度**：
- 額度預報：照目前速度什麼時候會撞到上限
- 分流建議：「Codex 滿了，Claude 還剩 70%」
- 「快重置了，額度還沒用完」的提醒
- 額度重置時發通知

**洞察**：
- 每個 repo、每個 PR 的 AI 成本
- subagent、thinking、各模型的使用比例
- 使用時段熱力圖

**Homelab**：
- 現在能跑哪些模型：用剩餘的 VRAM 判斷
- 智慧插座的實測耗電（Shelly、Tasmota、Kasa、Home Assistant）
- Wake-on-LAN
- 找出多台機器上重複存放的模型檔
- 模型放置建議

**整合**：
- MCP server：讓 agent 自己查預算
- Discord 和 Telegram 週報
- 實驗室彙總模式（只顯示總量）
- 研究計畫核銷用的 CSV 和 PDF 匯出
- Prometheus 和 Grafana

**分享**：
- 年度回顧卡
- 成就系統


## Token Monitor 參考與原生狀態列（2026-10-04）

使用者確認先前提到的是 [Javis603/token-monitor](https://github.com/Javis603/token-monitor)。
參考的是本機 token 細項與 CLI 旁的即時資訊；本次不移植程式碼或任何 credential 讀取方法。
[Claude Code 官方 statusline](https://code.claude.com/docs/en/statusline) 驗證 current_usage 四欄，
input 不含快取；context occupancy 只含三種輸入，不含 output。上下文總數屬目前視窗，不是 session 累計。
null 出現在首次 API 前／compact 後；COLUMNS 由 Claude 設定。只顯示白名單欄位，從不開 transcript。

## 個人歷史 Profile 驗證（2026-10-04）

`--profile` 以既有 usage 表建立累計／實際有紀錄的曆月／曆年區間，依本機時區分日，排除未來與 cloud GPU 列。
reasoning 是 output 子集合；零成本的本地 token 也列入活躍日。每個來源另列可見日期與筆數，不冒充完整 GUI／帳號歷史。
來源依 backend 格式歸類，不能據此區分 T3 Code 與 Codex GUI，也不從 token 量推論工作內容或能力。
價格只用現行設定的已定價部分重算 API 等值，不採歷史訂閱付款假設。原帳本保留，本機報告從快照產生。
合成測試覆蓋跨年、曆日間距、cache write、reasoning 不重算、本地零成本、未定價、空歷史、HTML 注入與彙總隱私；
另以 Node DOM harness 驗證區間／雜湊連結／深淺色／列印，CLI 同步白名單不包含 API 或遠端裝置。
本次未新增資料來源，沿用現有 parser fixtures；真實個人報告只留本機、不進 git。
