# ComputAI 使用手冊

ComputAI 把所有花你算力和 AI 錢的東西記在同一本帳（一個 SQLite 檔）裡，再從帳本產生報表。
這份手冊說明怎麼設定、每個指令、設定檔，以及數字是怎麼算出來的。English: [MANUAL.md](MANUAL.md)。

- [檔案放在哪裡](#檔案放在哪裡)
- [訂閱：Claude Code 和 Codex](#訂閱claude-code-和-codex)
- [指令](#指令)
- [設定檔](#設定檔)
- [機器和本地模型](#機器和本地模型)
- [token 計數 proxy](#token-計數-proxy)
- [雲端 GPU](#雲端-gpu)
- [組織的 API 用量](#組織的-api-用量)
- [分析](#分析)
- [總帳畫面](#總帳畫面)
- [數字怎麼算](#數字怎麼算)
- [疑難排解](#疑難排解)

## 開始設定

`computai --setup` 一次問一件事，把下面所有設定走一遍，確認後才寫入 `config.ini`（舊檔留成
`config.ini.bak`）。`computai --doctor` 檢查每個來源和每台機器，印出修正每個缺口的指令。
`computai --set 段落.鍵=值` 和 `--unset 段落.鍵` 改單一設定，不會動到你的註解。
`computai --discover --add` 把連得上的機器都加進來，並依硬體填好功耗建議值。

## 檔案放在哪裡

| 東西 | 預設位置 | 改位置 |
|---|---|---|
| 設定（`config.ini`、`prices.ini`、`secrets.ini`） | `~/.config/computai/`（Windows：`%APPDATA%\computai`） | `COMPUTAI_CONFIG_DIR`、`XDG_CONFIG_HOME` |
| 帳本（`ledger.sqlite`） | `~/.local/share/computai/`（Windows：`%LOCALAPPDATA%\computai`） | `COMPUTAI_DATA_DIR`、`XDG_DATA_HOME` |
| Claude Code 的 log | `~/.claude/projects/`、`~/.config/claude/projects/` | `CLAUDE_CONFIG_DIR`（可用逗號列多個） |
| Codex 的 log | `~/.codex/sessions/`、`~/.codex/archived_sessions/` | `CODEX_HOME` |

`computai --paths` 會印出前兩個位置。第一次執行時會從範本建立 `config.ini` 和 `prices.ini`，之後只讀不寫，
你改的內容會保留。刪掉帳本是安全的：下次 `--sync` 會從 log 重建訂閱的歷史（機器取樣和雲端紀錄會不見）。

## 訂閱：Claude Code 和 Codex

不用設定。`computai --sync`（以及所有報表，除非加 `--no-sync`，都會先同步）會讀新的 log，
只重讀上次之後有變動的檔案。

- **Claude Code**：每個 API 回應一列，用 message id 和 request id 去重。串流時同一個回應會被寫好幾次，
  ComputAI 保留最完整的那份。快取寫入分 5 分鐘和 1 小時；thinking token 另外記（它算在 output 裡）；
  subagent 的請求會標記；工作目錄就是專案。
- **Codex**：每個 `token_count` 事件一列。OpenAI 的 `input_tokens` 包含快取命中的部分，
  ComputAI 會扣掉，讓兩家的欄位意思一致。加總跟 Codex 自己記的每個 thread 的 `tokens_used` 一樣。
- **額度**：Codex 的 log 有額度視窗（`rate_limits`），顯示成 `week`、`5h` 等。Claude 的額度只會傳給
  statusline 指令，所以要把 Claude Code 的 statusLine 設成 `computai --statusline`
  （見 [one-line.md](one-line.md)），限 Pro、Max 帳號。

## 指令

每個指令都可以加 `--json`。時間範圍：`--month [YYYY-MM]`、`--since YYYY-MM-DD`、
`--until YYYY-MM-DD`（含當天）；預設是這個月。

| 指令 | 做什麼 |
|---|---|
| `computai` | 在終端機裡是 live 畫面；不在終端機（例如被其他程式呼叫）就等於 `--summary`。 |
| `--summary [--by model\|project\|session\|day]` | 每個來源、每個模型的總量、等值 API 花費、方案比較、額度、機器、雲端和警示。 |
| `--sync` | 匯入新的用量，印出每個來源新增幾筆。 |
| `--line [--sep " · "]` | 一行字：每個訂閱最吃緊的額度視窗、今天的花費。最多每 30 秒重讀一次 log。 |
| `--statusline` | 給 Claude Code 的 `statusLine` 用：從 stdin 記下 Claude 的額度，印出 `--line`。 |
| `--live [-n 秒]` | 終端機 live 畫面：每台機器一個面板（CPU、記憶體、每張 GPU、功耗的長條和走勢，以及推論服務），AI 用量（額度長條、14 天花費走勢），警示。寬的終端機分兩欄，視窗太矮時每台機器縮成一行。按 `q` 離開。 |
| `--once` | 印一次 live 畫面就結束（會先讀 log、取樣機器）。 |
| `--lang zh` | live 畫面、網頁版和 `--line` 用繁體中文（也可以設 `[general] lang = zh`）。 |
| `--web [[位址:]埠]` | 瀏覽器版（手機排版）、`/api/state` JSON、給 Prometheus 的 `/metrics`。預設 `127.0.0.1:8765`。 |
| `--recap [年份] [--html 檔名]` | 年度回顧（token、方案划算程度、使用天數、最長連續天數、最忙的一天、最常用的模型、本地推論）；HTML 卡片不含專案和機器名稱，可以直接分享。月費以「有用量的月份 × 目前 `[plans]` 的價格」計算。 |
| `--weekly [--send]` | 最近 7 天的幾行摘要；`--send` 會送到 `DISCORD_WEBHOOK_URL` 和／或 Telegram（`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`，跟其他金鑰一樣從環境變數或 secrets.ini 讀）。放進 cron 就是每週通知。 |
| `--totals 檔名 [--who 名字]`／`--lab 資料夾` | 實驗室彙總：每個人把自己這個月的總額（每個來源、模型的花費和 token、度數；不含專案名稱）寫到共用資料夾，`--lab` 把整個資料夾合成一張表。 |
| `--csv 檔名` | 範圍內每一筆用量（時間、來源、模型、專案、token、金額）輸出成 CSV；`= + - @` 開頭的文字前面會加 `'`，避免試算表把它當公式執行。 |
| `--report [--html 檔名]` | 月報，文字版或一個獨立的 HTML 檔（含每日花費圖）。 |
| `--analyze` | 月底預測、方案檢查、快取效率、電費分析。 |
| `--payback 美元 [--gpu-watts W --hours-per-day H --rent-per-hour 美元]` | 買一張卡跟租雲端比，多久回本。 |
| `--discover` | 從 `~/.ssh/config` 和 Tailscale 找機器，逐台試 SSH，說明連不上的原因，並印出可以貼進 `[machines]` 的設定。 |
| `--wake 名稱` | 對 `[machine.名稱]` 裡有設 `mac = ...`（可選 `wol_address = ...`）的機器送 Wake-on-LAN 封包。 |
| `--sample` | 讀一次每台機器，印出機器表。 |
| `--cloud` | 列出 RunPod、Vast.ai、Lambda 的機器並記下花費。 |
| `--proxy [--listen ... --upstream ... --machine 名稱]` | Ollama 和 OpenAI 相容服務的 token 計數 proxy。 |
| `--mcp` | 給 agent 用的 MCP server（見下面）。 |
| `--paths`、`--version` | |

`--live`、`--web`、`--proxy` 會一直執行；執行期間每 30 秒重讀 log、每 `--sample-every` 秒
（預設 60）取樣機器，有設金鑰的話每 5 分鐘查一次雲端。

## 設定檔

`config.ini`（`#` 或 `;` 開頭是註解，行尾註解前面要有空白）：

```ini
[general]
usd_to_local = 32        ; 匯率，電價用其他幣別時換算用
local_currency = TWD

[plans]                  ; <來源> = <方案名稱>, <每月美元>, <查價日期>
claude = Claude Max 5x, 100, 2026-10-03
codex = ChatGPT Pro, 200, 2026-10-03

[plan_options]           ; 方案模擬器用：<名稱> <美元> x<額度倍數>
claude = Pro 20 x1, Max 5x 100 x5, Max 20x 200 x20
codex = Plus 20 x1, Pro 200 x20

[machines]               ; <名稱> = local 或 <ssh 主機>
this-computer = local
gpubox = gpubox.tailnet

[machine.gpubox]
services = ollama:11434, vllm:8000
base_watts = 80          ; GPU 以外的部分，加在量到的 GPU 功耗上
cpu_watts = 90           ; CPU 全速時多出來的功耗，照 CPU 使用率比例加上（CPU 推論、編譯）
plug = shelly:192.168.1.50  ; 智慧插座實測功耗：shelly、shelly1（第一代）、tasmota，
                         ; 或 ha:sensor.x（Home Assistant，要設 HA_URL、HA_TOKEN 金鑰）
[machine.this-computer]
idle_watts = 6           ; 讀不到 GPU 功耗時（Mac）：照負載在閒置和滿載之間內插
max_watts = 30

[power]
price_per_kwh = 0.15
currency = USD
tariff = flat            ; 或 tou，見下面
idle_alert_minutes = 15  ; 模型載入卻這麼久沒用 -> 警示

[budget]
monthly_usd = 0          ; 0 = 不設預算

[cloud]
idle_gpu_util = 5        ; 計費中的 GPU 使用率低於這個 % 就算閒置
idle_alert_minutes = 20
ssh_user =               ; API 沒有 GPU 使用率時（Lambda）用這個帳號 SSH 進去讀
```

`prices.ini` 是每百萬 token 的 API 價格（`input`、`output`、`cache_read`、`cache_write_5m`、
`cache_write_1h`，加上 `checked`、`source`）。沒有自己段落的模型，會用名稱是它開頭的最長段落，
所以 `[claude-sonnet-5]` 也涵蓋 `claude-sonnet-5-5`。fast mode 用 `<模型>@fast` 計價。
沒有價格的模型會列在 `--summary` 最後一行，自己加一段就好。

`secrets.ini`（權限一定要 600，否則會警告並忽略）：

```ini
[secrets]
RUNPOD_API_KEY = ...
VAST_API_KEY = ...
LAMBDA_API_KEY = ...
ANTHROPIC_ADMIN_KEY = ...
OPENAI_ADMIN_KEY = ...
```

同名的環境變數優先。

### 時間電價（台電）

在 `[power]` 設 `tariff = tou`。`tou_*` 這幾個值用 `tou_utc_offset` 時區的當地時間描述電價：
哪幾個月是夏月、夏月和非夏月的尖峰時段、四個價格、週末是否全天離峰。預設是台電表燈簡易型時間電價
二段式；**沒能跟台電官網核對，請對照你的電費單**。台灣用戶通常會一起設 `currency = TWD` 和
`[general] usd_to_local`。用時間電價時，耗電會照使用的時間點計價，`--analyze` 會算出 AI 工作有多少在
尖峰跑、挪到離峰可以省多少。

## 機器和本地模型

`computai --discover` 會從 `~/.ssh/config` 和 Tailscale 列出候選機器、逐台試 SSH，並印出要加的設定。
`[machines]` 裡每台機器用一次 `ssh` 跑一段 POSIX `sh` 腳本來讀（`local` 就在本機跑）。
機器上需要：`sh`，以及 `curl` 或 `wget`（看推論服務用）。SSH 要能不經提示就登入
（`ssh -o BatchMode=yes 主機 true` 要成功）；25 秒內沒回應的機器那一輪會略過。

讀的東西：CPU、記憶體、NVIDIA GPU（`nvidia-smi`）、AMD GPU（sysfs）、Apple GPU（`ioreg`），
以及機器自己 loopback 上的推論服務：

| 服務 | 預設埠 | 讀什麼 |
|---|---|---|
| Ollama | 11434 | `/api/ps`：載入的模型和佔的記憶體 |
| llama.cpp（要加 `--metrics`） | 8080 | `/metrics`：prompt 和生成的 token、處理中的請求 |
| vLLM | 8000 | `/metrics` |
| SGLang（要加 `--enable-metrics`） | 30000 | `/metrics` |
| LM Studio | 1234 | `/api/v0/models`：載入的模型 |
| 其他 OpenAI 相容（MLX 等） | 自己設 | `/v1/models` |

每台機器可以用 `services = 種類:埠, ...` 改要看的服務。兩次取樣之間 token 計數器增加的部分，會記成
`local` 用量（花費 $0，成本在電費）。Ollama 沒有 metrics，token 數要靠 proxy；但 ComputAI 還是看得出
Ollama 有沒有在用：每個請求都會把模型的 `expires_at` 往後推。

**警示**：模型載入後 `idle_alert_minutes` 分鐘都沒活動，會出現「loaded but idle (holding N MB)」。

## token 計數 proxy

```sh
computai --proxy                                   # 127.0.0.1:11435 -> http://127.0.0.1:11434
OLLAMA_HOST=127.0.0.1:11435 ollama run qwen3:0.6b  # 讓用戶端改連 proxy
```

proxy 原樣轉送所有內容，只讀回應裡的用量欄位（Ollama 的 `prompt_eval_count`／`eval_count`、
OpenAI 的 `usage`、Responses API 的 `response.usage`）。OpenAI 的串流請求如果沒要求用量，
會替它加上 `stream_options.include_usage`，不然串流回應裡根本沒有 token 數；不要這樣做就加
`--no-usage-injection`。token 記在 `--machine` 這台（預設是第一台 `local` 機器）。
聽 loopback 以外的位址會警告：連得到這個埠的人都能用你的模型。

## 雲端 GPU

設定 `RUNPOD_API_KEY`、`VAST_API_KEY`、`LAMBDA_API_KEY` 其中幾個，執行 `computai --cloud`
（或讓 `--live`／`--web` 開著）。只會呼叫唯讀的「列出我的機器」API。

- RunPod：狀態、價格、GPU 從 REST API 讀；GPU 使用率從 GraphQL API 讀。
- Vast.ai：狀態、`dph_total`、GPU 使用率；停機的機器還會收 `storage_cost`。
- Lambda：狀態和價格；API 沒有 GPU 使用率，可以設 `[cloud] ssh_user`（通常是 `ubuntu`）用 SSH 讀 `nvidia-smi`。

每次查詢存一份快照；兩次快照之間的時間照每小時價格計費（間隔超過 6 小時的不亂猜）。
**閒置還在計費**：GPU 使用率低於 `idle_gpu_util` % 持續 `idle_alert_minutes` 分鐘就警示，並列出閒置期間花掉的錢。

## 組織的 API 用量

有 `ANTHROPIC_ADMIN_KEY`（`sk-ant-admin...`）或 `OPENAI_ADMIN_KEY` 時，`--sync` 也會從 admin 用量 API
匯入組織每天每個模型的用量（第一次 31 天，之後從上次同步的前一天開始）。訂閱（Pro、Max、Plus）的用量不在這些 API 裡。

## 分析

`computai --analyze`（快取報告用你選的範圍，其他用這個月）：

- **月底預測**：訂閱月費 + 這個月已經花的錢（雲端、API、電費）+ 最近 7 天的日均 × 剩下的天數。
  另外推估每個訂閱照目前速度的等值 API 花費。設了 `[budget] monthly_usd` 會有超支警示。
- **方案檢查**：用過去 30 天額度視窗的最高使用率，乘上方案倍數換算，挑出最便宜、而且會低於 90% 的方案。
  如果等值 API 花費比最便宜的方案還低，會告訴你直接付 API 比較便宜。
- **快取效率**：同一個 session、同一個模型裡，一個請求把一半以上的 context 重新寫入快取就算一次重寫；
  浪費 = 這些 token 的快取寫入價減去讀取價。停超過快取壽命（5 分鐘或 1 小時）之後的重寫另外計算：
  那是 session 放著不動造成的。
- **電費**：本地每生成一百萬 token 的電費，以及挪到離峰可以省多少。

`computai --payback 1800 --gpu-watts 450 --hours-per-day 8` 比較買卡和租雲端：租金用 `--rent-per-hour`，
沒給就用你的雲端紀錄（每張卡）。時間電價下假設工作盡量排在離峰。

## 總帳畫面

- `computai`／`--live`：算力（每台機器一個面板，框線顏色跟著負載變，跟 slurmtop 一樣：CPU、記憶體、
  每張 GPU 的使用率／VRAM／溫度／功耗、功耗走勢，以及每個推論服務載入的模型和 token 速率）、AI 用量、警示，
  每 `-n` 秒更新。`--once` 只印一次；終端機畫不出方塊字時自動改用 ASCII。
- `--web`：打開 `http://127.0.0.1:8765/`。要在手機上看，保持只聽 loopback，用 SSH tunnel
  （`ssh -L 8765:127.0.0.1:8765 主機`）或 `tailscale serve 8765`。`--web 0.0.0.0:8765` 會把你的用量、
  專案名稱、機器公開給整個網路，會印出警告。
- `/metrics`：`computai_` 開頭的 gauge（每個來源的當月花費和 token、額度使用率、機器 CPU／GPU／功耗、
  雲端價格和 GPU 使用率、預測、各類警示數量）。
- `--report --html 檔名`：一個可以保存或寄出的 HTML 檔。

## MCP server（給 agent 用）

`computai --mcp` 在標準輸入輸出上說 Model Context Protocol，讓 agent 在做花錢的事之前自己查預算。
工具有：`usage_summary`（某個月每個來源、每個模型的花費）、`limits`（額度）、`budget`（月底預估和今天）、
`machines`（GPU 使用率、載入的模型、還放得下多大的模型）、`advice`（建議）。全部唯讀。
在 agent 裡把它註冊成 stdio server，指令是 `computai --mcp`（Claude Code 大概是
`claude mcp add computai -- computai --mcp`；Codex 是在設定加一段 `[mcp_servers.computai]`，
`command = "computai"`、`args = ["--mcp"]`）。

## 數字怎麼算

- **等值 API 花費** = token × `prices.ini` 的價格，查詢時才算，所以改價格會連過去的月份一起變。
  雲端的紀錄自帶金額。
- **耗電**：相鄰兩次取樣的平均功耗 × 間隔時間。間隔超過 10 分鐘的那段不算，所以機器表的 `hours`
  代表實際涵蓋了多少時間。讀得到 GPU 功耗時，功耗 = GPU + `base_watts`；讀不到就照負載在
  `idle_watts` 和 `max_watts` 之間內插。
- **AI 佔比**：取樣時間裡機器在做推論的比例：token 計數器有動、有請求在跑、proxy 有流量、Ollama 的
  `expires_at` 有動，或（非 Apple 的 GPU）有模型載入且 GPU 忙超過 20%。Mac 的 GPU 使用率包含畫面繪製，
  不拿來判斷。
- **J/token** = AI 時段的能量 ÷ 生成的 token 數。

## 疑難排解

- *某個模型的花費顯示「?」*：在 `prices.ini` 加上它的價格。
- *看不到 Claude 的百分比*：設定 `computai --statusline`（限 Pro／Max）。
- *機器一直沒出現*：`--sample`、`--live`、`--web` 會顯示原因（「cannot read: ...」）。執行
  `ssh -o BatchMode=yes 主機 true`，必須不經提示就成功。「Host key verification failed」表示 known_hosts
  裡這台的 key 記在別的名字下：改用你平常 ssh 用的名字或 IP（Tailscale 的機器常常是 100.x 的位址），
  或先手動 `ssh 主機` 一次。
- *「ignoring secrets.ini」*：`chmod 600 ~/.config/computai/secrets.ini`。
- *想重來*：刪掉 `ledger.sqlite`，下次執行會重新匯入 log。
- *移除*：刪掉 `computai` 檔案、`~/.config/computai` 和 `~/.local/share/computai`。
