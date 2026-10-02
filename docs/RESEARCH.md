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

## 點子清單

**優先**：
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
