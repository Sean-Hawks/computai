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

直接輸入 `computai` 先顯示六項功能。直接 Enter 進監控；`2` 做月報、`3` 自動開網頁、
`4` 看花費分析、`5` 檢查資料來源、`6` 設定環境。輸入數字後按 Enter；`0`、`q`、Ctrl-C 或 EOF 離開。
只看選單不會讀用量、連線機器或建立設定與帳本。非互動環境會印指南後結束；腳本查用量用 `--summary` 或 `--json`。
beta.3 以前的裸指令會直接進監控。

從選單進監控不會先問月費。第一次直接執行 `computai --live`、又還沒設月費時，每個訂閱只問一句：Codex 用 log 裡記錄的方案，Claude 照近 30 天的用量猜。
Enter 確認、`n` 跳過，或打別的方案名稱。只問這一次，之後用 `computai --setup` 改。

## 檔案放在哪裡

| 東西 | 預設位置 | 改位置 |
|---|---|---|
| 設定（`config.ini`、`prices.ini`、`secrets.ini`） | `~/.config/computai/`（Windows：`%APPDATA%\computai`） | `COMPUTAI_CONFIG_DIR`、`XDG_CONFIG_HOME` |
| 帳本（`ledger.sqlite`） | `~/.local/share/computai/`（Windows：`%LOCALAPPDATA%\computai`） | `COMPUTAI_DATA_DIR`、`XDG_DATA_HOME` |
| Claude Code 的 log | `~/.claude/projects/`、`~/.config/claude/projects/` | `CLAUDE_CONFIG_DIR`（可用逗號列多個） |
| Codex 的 log | `~/.codex/sessions/`、`~/.codex/archived_sessions/` | `CODEX_HOME`（可用逗號列多個；帳號額度問第一個） |

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
- **額度**：兩家都讀整個帳號的數字（別台電腦、T3 Code、claude.ai、別人用的都算）。多久查一次跟著消耗速度走：
  - 沒有快用完的額度時每 `poll_minutes`（預設 10 分鐘）一次；燒得快時加快，最短 1 分鐘（剩餘 % ÷ 消耗速度 ÷ 4）。
    變快立刻採用，變慢則慢慢放鬆，不會剛停下來就回到慢速。
  - 任何視窗的重置時間一到，過 30 秒多查一次，恢復的數字馬上看得到。
  - 消耗速度用帳本裡同一個視窗的連續樣本算。`computai --doctor` 會顯示下次查詢的時間和原因
    （「每週額度照速度 3h00m 後用完 → 每 45m」）；`[limits] refresh = fixed` 改回固定每 `poll_minutes` 一次。
  - Claude：問官方的 `claude` 程式（`claude -p /usage`，本機指令，不呼叫模型、不花額度），限 Pro、Max 帳號。
    也可以把 Claude Code 的 statusLine 設成 `computai --statusline`（見 [one-line.md](one-line.md)），每次回應都會更新。
  - Codex：問官方的 `codex` 程式（`codex app-server`）；log 裡的額度視窗也會讀。
  - 登入都由官方程式自己處理，ComputAI 只拿到百分比和重置時間。`[claude]`／`[codex] poll_minutes = 0` 關掉。

### 其他 agent：Gemini CLI、OpenCode、Cursor

一樣只取用量欄位：

- **Gemini CLI**：`~/.gemini/tmp/<專案>/chats/*.jsonl`（可以用 `GEMINI_CLI_HOME` 改位置）。每則 Gemini 回應一列，用 id 去重；
  `input` 含快取、`output` 不含 thinking，ComputAI 會扣掉、加回（用真實紀錄核對過：total = input + output + thoughts + tool）。
  subagent（`kind: subagent`）算在主 session 底下。
- **OpenCode**：`~/.local/share/opencode/opencode*.db`（和舊版的 `storage/message/*.json`）。只讀 assistant 訊息的中繼資料，
  使用唯讀連線，也會讀到 WAL 中已提交的更新；不複製含對話內容的資料庫、不查詢 `part` 表。
  OpenCode 的 input、output、reasoning、快取互不重疊，
  子 session 算 subagent；OpenCode 有算出花費時就用它的。
- **Cursor** 在你的電腦上沒有 log。到 cursor.com/dashboard（Usage → Export CSV）匯出，然後 `computai --import-cursor 檔案`，
  或設 `[cursor] exports = ~/Downloads/usage-events*.csv` 讓每次同步自動匯入。欄位照標題名稱找；格式來自第三方的解析程式，
  還沒用真的匯出檔核對過。「Errored, No Charge」的列不算；重疊的匯出檔重複匯入不會重複計算。

## 指令

每個指令都可以加 `--json`。時間範圍：`--month [YYYY-MM]`、`--since YYYY-MM-DD`、
`--until YYYY-MM-DD`（含當天）；預設是這個月。

| 指令 | 做什麼 |
|---|---|
| `computai` | 功能選單，Enter 進監控；非互動環境印指南後結束。 |
| `--summary [--by model\|project\|session\|day]` | 每個來源、每個模型的總量、等值 API 花費、方案比較、額度、機器、雲端和警示。 |
| `--sync` | 匯入新的用量，印出每個來源新增幾筆。 |
| `--line [--sep " · "]` | 一行字：每個訂閱最吃緊的額度視窗、今天的花費。最多每 30 秒重讀一次 log。 |
| `--statusline` | 給 Claude Code 的 `statusLine` 用：從原生 stdin 記下額度並顯示模型、上下文、上次請求；`--statusline-view compact` 保留單行。 |
| `--live [-n 秒]` | 終端機 live 畫面：每台機器一個面板（CPU、記憶體、每張 GPU、功耗的長條和走勢，以及推論服務），AI 用量（額度長條、14 天花費走勢），警示。寬的終端機分兩欄，視窗太矮時每台機器縮成一行。按 `q` 離開。 |
| `--once` | 印一次 live 畫面就結束（會先讀 log、取樣機器）。 |
| `--card --setup` | 幾個問題設定好 GitHub 個人頁卡片（找到或 clone 個人頁 repo、產生第一張卡片、加進 README）。 |
| `--watch` | 不開畫面：在背景更新帳本並送通知（見「通知」）。 |
| `--claude-limits` | 現在就透過 claude 程式讀 Claude 帳號的額度（`claude -p /usage`，不呼叫模型）。 |
| `--codex-limits` | 現在就透過 codex 程式讀 Codex 帳號的額度（包含別台電腦、別人用的）。 |
| `--limit-reset claude\|codex` | 手動標記某個訂閱的額度已經重置（提早重置時 log 看不到）；下次讀到真的數字就會取代。 |
| `--notify-test` | 送一則測試通知。 |
| `--install-watch`／`--uninstall-watch` | 登入時自動在背景跑 `--watch`，或取消。 |
| `--bench [--machine 名稱]` | 每個本地模型跑幾秒：每秒 token、功耗、每 token 焦耳、每百萬 token 電費和 API 比較。 |
| `--theme cyber\|classic` | 深色、安靜的 cyberpunk 儀器風格（預設，見 [DESIGN.md](DESIGN.md)）或 slurmtop 樣式，終端機、網頁、月報、回顧卡都會套用（也可以設 `[general] theme`）。 |
| `--lang zh` | live 畫面、網頁版和 `--line` 用繁體中文（也可以設 `[general] lang = zh`）。預設 `lang = auto` 跟系統語言走；macOS 以系統偏好的語言為準，因為 cmux、Ghostty 等終端機不管系統語言都會設 `LANG=en_US`。想固定英文就設 `COMPUTAI_LANG=en` 或 `lang = en`。 |
| `--web [[位址:]埠]` | 瀏覽器版（手機排版）、`/api/state` JSON、給 Prometheus 的 `/metrics`。預設 `127.0.0.1:8765`。 |
| `--recap [年份] [--html 檔名]` | 年度回顧（token、方案划算程度、使用天數、最長連續天數、最忙的一天、最常用的模型、本地推論）；HTML 卡片不含專案和機器名稱，可以直接分享。月費以「有用量的月份 × 目前 `[plans]` 的價格」計算。 |
| `--wrapped [YYYY-MM\|YYYY] [--html 檔名] [--svg 檔名]` | 像 Spotify Wrapped 的月（預設：這個月到現在）或年回顧：終端機文字、限時動態風格網頁（`--html`）、1200x630 分享卡（`--svg`）。只有彙總數字和模型名稱。見「Wrapped 回顧」。 |
| `--card [--period 30d\|month\|year\|all] [--card-theme dark\|light] [--svg 檔名] [--publish 路徑 [--push]]` | 放在 GitHub 個人頁 README 的小 SVG 卡片。見「個人頁卡片」。 |
| `--weekly [--send]` | 最近 7 天的幾行摘要；`--send` 會送到 `DISCORD_WEBHOOK_URL` 和／或 Telegram（`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`，跟其他金鑰一樣從環境變數或 secrets.ini 讀）。放進 cron 就是每週通知。 |
| `--totals 檔名 [--who 名字]`／`--lab 資料夾` | 實驗室彙總：每個人把自己這個月的總額（每個來源、模型的花費和 token、度數；不含專案名稱）寫到共用資料夾，`--lab` 把整個資料夾合成一張表。 |
| `--csv 檔名` | 範圍內每一筆用量（時間、來源、模型、專案、token、金額）輸出成 CSV；`= + - @` 開頭的文字前面會加 `'`，避免試算表把它當公式執行。 |
| `--report [--html 檔名]` | 月報，文字版或一個獨立的 HTML 檔（含每日花費圖）。 |
| `--profile [all\|YYYY-MM\|YYYY] [--html 檔名]` | beta.3：個人用量頁，切換累計、月報、年報，附涵蓋日期與精確 token 細項。 |
| `--create [--html 檔名] [--no-open]` | beta.3：本機製卡頁，自動開瀏覽器，選範圍／版型後下載 PNG 或 SVG；不需要 GitHub 設定。 |
| `--profile --share-layout square\|portrait\|wide [--svg 檔名] [--html 檔名]` | beta.3：Web／TUI 風格的一頁社群圖卡，分享頁可下載原尺寸 PNG。 |
| `--analyze` | 月底預測、方案檢查、快取效率、電費分析。 |
| `--payback 美元 [--gpu-watts W --hours-per-day H --rent-per-hour 美元]` | 買一張卡跟租雲端比，多久回本。 |
| `--discover` | 從 `~/.ssh/config` 和 Tailscale 找機器，逐台試 SSH，說明連不上的原因，並印出可以貼進 `[machines]` 的設定。 |
| `--wake 名稱` | 對 `[machine.名稱]` 裡有設 `mac = ...`（可選 `wol_address = ...`）的機器送 Wake-on-LAN 封包。 |
| `--sample` | 讀一次每台機器，印出機器表。 |
| `--cloud` | 列出 RunPod、Vast.ai、Lambda 的機器並記下花費。 |
| `--proxy [--listen ... --upstream ... --machine 名稱]` | Ollama 和 OpenAI 相容服務的 token 計數 proxy。 |
| `--tokens` | 最近 30 天的 token 精確細項、快取占比及來源／模型／專案排名；支援日期與 JSON。beta.3。 |
| `--local-requests [筆數] [--tag test/production/benchmark]` | 今天新版 proxy 請求的耗時、HTTP 結果及輸出／全程 tok/s；支援日期／機器／模型篩選。beta.3。 |
| `--local-history [筆數] [--machine 名稱] [--model 模型]` | 最近本地用量，預設今天最新 20 筆，最多 200 筆；支援日期範圍與 `--json`。beta.3 新增。 |
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

## 其他電腦

額度是整個帳號的，但 token 和花費來自這台的 log。要把筆電、公司電腦或 homelab 加進來（[細節](MULTI-DEVICE.md)）：

- **共用資料夾**（推薦）：每台都 `computai --set devices.folder=路徑`，指向一個它們都會同步的資料夾（iCloud Drive、
  Dropbox、Syncthing、私人 git repo）。每台把自己的用量寫進去（沒有 prompt 或完整路徑，session id 只留裝置／來源範圍內的單向雜湊），
  再讀別台的。`devices.name` 設定顯示的名字。
  匿名 session 修正已在 beta.2 釋出，本版也已包含；已匯入的舊資料可依[升級步驟](MULTI-DEVICE.md#從沒有-session-的舊格式升級)補回分組。
- **SSH 拉取**：`[machines]` 裡的機器加上 `[machine.X] usage = pull`。ComputAI 會把自己複製到對方的
  `~/.cache/computai`（對方只需要 `python3`），再執行 `computai --export-usage`。

不管從哪條路來，每一筆只算一次。檔案壞掉時整份略過，之前的數字照留。超過 10 分鐘沒回報的裝置會標成過時。
`--summary` 會列出每台，`--summary --by device` 照裝置拆開，`--doctor` 顯示每台最後回報的時間和錯誤。

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

- `--live`（或選單直接 Enter，cyber 主題）有分頁：**1 總覽**（一個畫面放得下：額度油表、每台機器一行、花費、最重要的警示和建議）、**2 額度**、**3 機器**、**4 本地模型**、**5 花費**、**6 時間軸**；`1`-`6` 或 `Tab` 切換，`q` 離開。按 `h` 或 `?` 看按鍵與功能指令，資料載入中也能使用；再按 `h`、`?` 或 Esc 返回，`c` 開製卡頁。額度預設看「剩下多少」（`[general] limits = used` 改回已用）。各面板由上到下：
  - **總結列**：一切正常、注意或警告，加上最嚴重的那件事（「Codex 每週額度用完了，4h43m 後重置 · 另外還有 1 件」）。
  - **額度**：每個額度視窗一條粗量表和百分比。白色的 `┃` 標出這個週期過了多久，長條超過它就代表用得比時間快。
    下一行寫「照目前速度 1h20m 後用完」或「重置時約 65%」。有用量卻沒有額度資料的訂閱，會告訴你怎麼接上。
  - **算力**：每台機器一個面板（CPU、記憶體、每張 GPU、功耗、推論服務和模型），下框線寫資料來源和多久前讀的。
  - **AI 訂閱與花費**：照 API 價格算的用量價值、月費、實際要付多少。
  - **警示**和**建議**。

  每 `-n` 秒更新。`--once` 只印一次；終端機畫不出方塊字時自動改用 ASCII。
- `--web`：打開 `http://127.0.0.1:8765/`。`--web 0.0.0.0:8765` 會把你的用量、專案名稱、機器公開給整個網路，
  會印出警告；要從手機或別台電腦看，改用下面的方法。
  - `computai --web --tailscale`（或直接 `computai --tailscale`）：伺服器仍然只聽 127.0.0.1，由 `tailscale serve`
    用 HTTPS 轉到你自己的 tailnet。會印出 `https://my-mac.tail1234.ts.net/` 這樣的網址，停止時（Ctrl-C、關掉終端機、
    服務停止）自動關掉轉發。不會搶別的 `tailscale serve` 已經在用的埠：443 被佔用就改用 8443 或 10000。
    沒有 Tailscale 時會說明怎麼裝，不會退回 `0.0.0.0`。`computai --install-watch --tailscale` 讓它常駐背景
    （服務跑的是 `--web --tailscale`，一樣會更新帳本和發通知）。
  - SSH tunnel：`ssh -L 8765:127.0.0.1:8765 主機`。
  - *Cloudflare Tunnel（還沒內建，規劃成進階選項）*：公開的網址任何人都連得到，所以 ComputAI 只會在那個網址前面設好
    [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/)（請求進來前先驗身分）時才開，
    否則拒絕並說明原因。自己手動設的話，先加 Access 政策，再把 tunnel 指到 `http://127.0.0.1:8765`。
- 網頁版的版面跟終端機總覽一樣：總結列、額度、四塊數字卡（今天和昨天比、本月的各方案回本倍數和要付多少、本地推論速度、
  功耗和趨勢線），接著是機器表、用量組成甜甜圈和「需要處理」（先警示、再建議），細節面板放在下面。全部用跟終端機同一份
  `dashboard_state()`。附上 web manifest 和圖示，手機透過 `--tailscale` 打開後可以「加到主畫面」，打開就像一個 App。
- `/metrics`：`computai_` 開頭的 gauge（每個來源的當月花費和 token、額度使用率、機器 CPU／GPU／功耗、
  雲端價格和 GPU 使用率、預測、各類警示數量）。
- `--report --html 檔名`：一個可以保存或寄出的 HTML 檔。

## 通知

有事情改變時，ComputAI 會主動告訴你，每件事只講一次：

- 額度到 80%（附照目前速度什麼時候用完）；
- 額度用完（附另一個訂閱還剩多少）；
- **額度重置、可以繼續用了**；
- 機器連不上、模型佔著記憶體沒在用、雲端 GPU 閒著還在計費；
- 這個月超過預算。

通知在 `computai`、`--web`、`--watch` 裡都會跑。狀態存在帳本裡，重開程式或同時跑好幾個都不會重複；
第一次執行只記下現況。

- `[notify] desktop = yes`（預設）：macOS 通知中心、Linux 的 `notify-send`、Windows 的氣泡通知。
- `[notify] chat = yes`：也送到 Discord／Telegram（`DISCORD_WEBHOOK_URL`、`TELEGRAM_BOT_TOKEN` +
  `TELEGRAM_CHAT_ID`）。
- `computai --notify-test`：送一則試試看。
- `computai --install-watch`：登入就在背景跑 `--watch`（macOS 用 launchd、Linux 用 `systemd --user`、
  Windows 用工作排程器）。`--uninstall-watch` 移除。

## 本地模型面板

「本地模型」面板（終端機和網頁）每台機器的每個模型一列：

- 是不是在推論、現在每秒幾 token；
- 今天和本月的 token；
- 照 API 價格值多少。價格用 `[local] compare_model`，沒設就用 `prices.ini` 最便宜的。

vLLM、llama.cpp、SGLang 自己會報 token 累計數。Ollama 不會，要在它前面接 token 計數 proxy：

1. 把 Ollama 搬到別的埠：`OLLAMA_HOST=127.0.0.1:11436 ollama serve`。
2. proxy 接手原本的埠：`computai --proxy --listen 127.0.0.1:11434 --upstream http://127.0.0.1:11436 --machine 名稱`。

用戶端照樣打 `:11434`，不用改。proxy 在 `/metrics` 提供累計數，取樣時透過 SSH 讀，所以遠端機器也行。

- 取樣若讀 proxy 的 Ollama 埠，或讀上游 vLLM／llama.cpp／SGLang 的 token 計數器，proxy 只交累計數。若只取樣原生 Ollama／LM Studio，proxy 仍逐筆記帳，避免漏帳。
- 給別台 computai 取樣時通常會自動避免重複記帳；明確 `--no-ledger` 只保留 `/metrics`，beta.3 也會停用逐筆請求紀錄。

## 自動更新的 GitHub 個人頁卡片

最快的方式是 `computai --card --setup`；README 有完整說明（每個區塊的意思、主題、隱私、疑難排解）。`computai --doctor` 會顯示卡片有沒有設定好、上次什麼時候更新。手動設定的方式：

在 `config.ini` 設定：

```ini
[card]
repo = ~/你的個人頁repo/assets
push = yes
```

`computai`、`--web` 或 `--watch` 每天會重寫一次那兩張卡片並 commit。

- `style` 選外觀：`netrunner`（預設）、`arasaka`、`militech`、`amber`、`matrix`、`synthwave`；`colors = #起, #迄` 可以自訂漸層。
- beta.3 另有 `minimal`、`paper`、`github`、`terminal`，分別為灰階橫幅、紙張直式、統計面板及等寬字終端風格。
- `layout = auto` 跟隨風格預設；可改成 `hud`、`compact`、`dashboard`、`portrait`，或用 `--card-layout` 暫時覆蓋。原本的 style 與 `mono`／`computai` 別名維持 HUD。
- `computai --card --html styles.html --lang zh` 產生本機比較頁：10 種風格的深淺色與 4 種版型。比較頁採各風格預設配色，附上產生 SVG 的指令；單張 SVG 與每日更新則使用自己的設定。
- `handle` 是標題上的名字，預設用 repo 的 GitHub 帳號。
- `lang` 是卡片的語言。
- `--setup` 會一項一項問，也會自動找到本機的個人頁 repo。推之前會先接上機器人推的 commit。

## 最近本地推論紀錄（beta.3）

這項功能自 `v0.1.0-beta.3` 提供。

```sh
computai --local-history --lang zh
computai --local-history 50 --machine m1m --model qwen3:8b --lang zh
computai --local-history 200 --since 2026-10-01 --until 2026-10-04 --json
```

每列顯示時間、模型、機器、輸入與輸出 token，以及記帳來源；輸入包含快取讀取。
`proxy` 是逐筆請求，會顯示請求數；「取樣差值」是兩次服務計數器之間的用量，請求數顯示 `-`，不能當成單一請求。
這只查現有帳本，不會觸發模型或重新匯入 log。沒有紀錄時，需先透過 proxy 或服務的 `/metrics` 記帳；無法還原未記錄的歷史。

TUI 分頁 **4 本地模型** 與網頁會顯示今天最新 8 筆；終端視窗較矮時會減少顯示筆數，並提示完整查詢指令。
已在執行的 TUI／網頁需重新啟動才會載入新版程式。紀錄僅含用量，不保存提示詞、回應、Claude Code 的任務內容、耗時或成功／失敗狀態。

## 本地模型的真實成本（`--local-cost`）

`computai --local-cost [--month]` 把每個本地模型跟小的雲端模型放在一起比：

- **每 100 萬 token 的電費**：用那台機器實測的 AI 耗電，照各模型的 token 分攤；沒有實際用量的模型改用最近一次
  `--bench` 的結果（標成「--bench 估的」）。
- **硬體**（可選）：`[local] hardware_usd` 和 `lifetime_years` 會加上每 100 萬 token 的折舊，以及打平點：
  每個月要跑多少 token，硬體才比各個 API 模型划算。
- **vs**：比 `[local] compare_models`（預設 `claude-haiku-4, gpt-5.4-mini`，輸入和輸出價格各半）便宜幾倍。
  比較的模型在 prices.ini 裡要有完全同名的一節，不然會直接說沒有，不會拿名字相近的模型來猜。
- **分流**：這個月 Claude、Codex 的輕量請求（輸出 ≤ `light_output`、上下文 ≤ `light_context`）如果都丟給最省的本地模型，
  可以省多少錢（照 API 價格）、多少訂閱用量，要花多少電。
- **碳排**：度數 × `[energy] grid_kg_per_kwh`。預設是台灣 113 年度電力排碳係數 0.474 公斤 CO2e/度
  （經濟部能源署 2025-04-14 公布）；可以改成你那裡的數字，或設 0 不顯示。

本地模型分頁和 Wrapped 會放一句話的版本：「這個月本地模型替你省了 $17，花了 0.6 度電」。

## 本地模型跑分

`computai --bench [--machine 名稱]` 對每個正在跑的推論服務，用同一段固定題目連續生成幾秒鐘。

- 量每秒幾個 token，並在生成時取樣功耗。
- 算出每 token 幾焦耳、每百萬 token 的電費，再和 `prices.ini` 裡最便宜的 API 輸出價格比（不算硬體成本）。
- 只讀回應裡的用量欄位。

Mac 要設定 `idle_watts`／`max_watts`（或接智慧插座）才有功耗欄位。

## 個人歷史 Profile（beta.3）

```sh
computai --profile --html profile.html --who hawks --lang zh
computai --profile 2026-09 --html september.html --lang zh
computai --profile 2026 --html annual.html --lang zh --no-sync
computai --profile --json --no-sync
```

打開 HTML，用「累計 Profile／月報／年報」或下拉選單切換；每月一覽也能直接點進月份。
停用 JavaScript 時會顯示全部區間。深淺色切換只影響這個頁面，列印可使用瀏覽器的「存成 PDF」。
每日長條依實際日期排列，不會把缺紀錄的日子壓縮；手機可橫向捲動，精確數字表可展開。

有用量天數按正數 token 計算，零花費的本地推論也算。總數為新輸入、快取讀取、兩種快取寫入與輸出相加，
不再加推理子集合、不含 GPU 租用紀錄。來源／模型占比的分母是這個區間的 token，模型只列前五名。
快取讀取占總數與輸入的快取讀取比例分開，後者的分母不含輸出。

最早／最新紀錄與筆數按來源列出；筆數不是請求數，本地計數器取樣可能涵蓋多次推論。
月份／年份未結束會標示「截至目前」，較早日期缺紀錄也會明示，不把有日期的報告當成完整帳號歷史。
來源名稱不代表使用哪個 GUI，無法補回未保存的 GUI／遠端紀錄，也不從 token 推測你的工作內容或能力。

API 等值按 `prices.ini` 的目前價格重算已定價部分，列出未定價模型，不使用訂閱月費推算歷史付款。
預設只匯入 Claude／Codex／Gemini／OpenCode／已保存的 Cursor 本機用量，不同步遠端裝置或雲端 API；
`--no-sync` 停止匯入。帳本既有其他來源的 token 仍會納入彙總。
`--json` 與 HTML 都含所有可見區間；日期參數只選擇 HTML 開啟時的報告，不裁切匯出資料。
只有日期、用量、來源、模型與衍生統計，不含 prompt、回應、專案、機器或 session；不會自動上傳。

### 一頁式社群圖卡

第一次製作執行 `computai recap`：自動找用量、選好月份並開啟月報頁，按「下載 PNG」即可分享。
`computai recap 2026-09` 指定月份，`computai recap --help` 查看少量相關選項；語言沿用設定或加 `--lang zh`。
原本 `--create` 仍可使用，`--recap YEAR` 的既有年報行為不變。
Web 的「做我的圖卡」與 TUI 的 `c` 使用同一頁。[完整製卡流程](MAKE-A-CARD.zh-TW.md)。

```sh
computai --profile --share-layout square --html share.html --svg share.svg --who hawks --lang zh
computai --profile 2026-09 --share-layout portrait --html month-share.html --lang zh --no-sync
computai --profile 2026 --share-layout wide --svg year-share.svg --lang zh --no-sync
```

`square` 1080×1080、`portrait` 1080×1350、`wide` 1200×630。SVG 預設採 Web／TUI 的黑白圓角面板，不繼承舊 `[card] style`／`colors`；
明確指定 `--card-style amber` 等舊風格才使用 HUD。`--who` 指定名稱，省略則使用已設定的 card.handle。語言依 `--lang` 或 general.lang。
畫面有日期／進行中註記、總 token（及精確整數）、快取讀取占比、輸出、有用量天數、最長連續天數、
來源占比與處理量最多的模型。直式另有曆日或月份長條，未結束的月份以 * 標示；長期累計只畫最近 12 個有紀錄月份。
來源列最多兩個來源加「其他」，模型排序按 token，包含快取。沒有附訂閱回本、付款、能力判斷或 session 名稱。

`--svg` 省略版型時預設 square；指定 --share-layout 而未給檔名時，SVG 輸出到 stdout（--json 仍輸出資料）。
`--html` 加任一分享選項時產生單張圖卡預覽，可在本機瀏覽器按「下載 PNG 圖卡」；canvas 使用 SVG 原尺寸，
不用安裝 Python 套件、不連外。也可下載 SVG，停用 JavaScript 仍能查看與下載 SVG。
分享 SVG／HTML 只包含所選區間，不會附其他月份的完整歷史；純 --profile --html 與 --json 仍包含所有區間。
圖片只寫到你指定的檔案或瀏覽器下載目錄，不會自動發社群貼文。

## Wrapped 回顧

`computai --wrapped [YYYY-MM|YYYY]` 是可以拿去分享的版本：token、照 API 價格算的價值、訂閱回本幾倍、活躍天數和最長連續天數、
最忙的一天和星期、最常工作的時段（本地時間）和對應的人格（夜貓子 0–4 點、早起的鳥 5–8 點、朝九晚五 9–17 點、夜晚駭客 18–23 點）、
token 佔比前三名的模型、對話數和最大那場的規模、提示快取省下的錢（快取命中 token × (輸入價 − 快取讀取價)）、
本地模型的 token 和度數、和上一段同樣長的期間比（進行中的月份，只拿上個月同樣天數比），
以及用輸出 token 換算的小比喻（每個 token 約 0.75 字：幾套《魔戒》（48 萬字）、以每分鐘 250 字算的閱讀小時數；
常數放在腳本的 `EQUIVALENTS`）。

- `--html 檔名`：全螢幕的故事頁，上方有進度條、一張一個大數字，點一下／輕觸（左邊三分之一是上一張）、方向鍵、空白鍵、
  手機左右滑動切換，最後一張是可以截圖分享的總結卡。單一檔案、不連網、沒有外部字型，尊重 `prefers-reduced-motion`。
  網址後面加 `#5` 可以直接從第 5 張開始。
- `--svg 檔名`：1200x630 的分享卡。
- `--json`：印出資料（含圖表用的每日數字）。

隱私：只有彙總數字和模型名稱，專案名稱、路徑、session id、機器名稱和 prompt 都不會進到頁面。月費以「目前 `[plans]` 的價格 × 有用量的月份」計算。

## 個人頁卡片

`computai --card --svg computai-card.svg` 寫出一張 495x195 的 SVG（像 github-readme-stats）：token、API 等值金額、最常用的模型、
活躍天數和連續天數，加上近 14 天的長條圖（`year`、`all` 則是近 12 個月）。`--period` 選範圍：`30d`（預設，最近 30 天，
滾動的區間，月初也不會是空的）、`month`、`year`、`all`。`--card-theme light` 輸出淺色版。純 SVG、行內屬性，沒有腳本、字型或圖片，
所有文字都經過跳脫。沒給 `--svg` 也沒給 `--publish` 時，SVG 印到標準輸出。

要放到 GitHub 個人頁：把兩個檔案放進你的個人頁 repo（跟帳號同名的那個）。

```sh
computai --card --publish ~/Documents/你的個人頁repo
git -C ~/Documents/你的個人頁repo push      # 或是在上面的指令加 --push
```

`--publish 路徑` 會把 `computai-card.svg` 和 `computai-card-light.svg` 寫進該路徑的 git repo，只用這兩個檔案做一個 commit
（卡片沒變就不 commit；其他已 stage 的檔案不受影響），並印出做了哪些事。沒有加 `--push` 絕對不會推出去；加了就是單純的 `git push`
（所以分支要有 upstream）。個人頁的 `README.md` 這樣寫：

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="computai-card.svg">
  <source media="(prefers-color-scheme: light)" srcset="computai-card-light.svg">
  <img alt="ComputAI card" src="computai-card.svg" width="495">
</picture>
```

卡片是當下的快照，要更新就再跑一次指令（可以放進 cron）。

## agent 時間軸

分頁 6（和 `computai --timeline`）只用時間戳和 token 數把當天畫成甘特圖。上方顯示日期、更新時間與整點刻度；
每列是一個有編號的 Claude／Codex session（在別台電腦跑的會加上 `@laptop`）或標明「本地」的模型。
subagent 縮排在主 session 底下，`↶` 表示跨日接續。

- `━` 是推估活動區段，`·` 是兩段請求間的空檔，`│` 是整點參考線，`┃` 是現在。
- 寬螢幕右側顯示累計活動時間與 token，每列下面顯示第一段開始至最後一段結束的時間範圍；累計時間不含中間空檔。
- 總結分開列出 Claude/Codex 與本地推論時數，兩者都是各列相加，同時執行會重疊計算。
- 活動區段依相隔不超過 5 分鐘的請求推估，單次請求至少畫 1 分鐘；不能據此判定實際任務內容或精確執行時間。
- 下方直接寫出最多同時、最長連續與最久空檔的時間；費用高峰標為 API 等值，不代表訂閱實際付款。

60 欄也可用；較窄時將每列時間放在第二行，TUI 高度不足時使用緊湊排列並標示省略的 session 數量。

`computai --timeline --svg 檔案` 輸出同一張圖的 SVG，不含專案名和機器名（列名是「Claude 1」「Codex 2」和本地模型名稱）；
Wrapped 裡會放最忙那天的時間軸。

## 小隊排行榜（`--team`）

完全選擇加入、不需要伺服器的朋友排行榜：每個人把「只有總數」的 JSON 推到同一個共用 git repo
（私人 repo，或 GitHub Gist——它也是 git repo）。

```sh
git clone <小隊的 repo 或 gist> ~/team
computai --set team.repo=~/team --set team.handle=neo
computai --team publish      # 先顯示完整 JSON，問過才 commit 並 push computai-team-neo.json
computai --team              # git pull 後顯示排行：這週 token、比上週、agent 小時、最多同時、連續天數
computai --team leave        # 刪掉自己的檔案並 push
```

檔案裡只有這週和上週的這四個數字、你的名字和時間：沒有專案名、路徑、模型、機器、IP、session。
讀別人的檔案時只接受預期的欄位，其他一律忽略。排行榜也會出現在花費分頁和 Wrapped 裡。

## 現在用哪個 agent（`--pick`）

ComputAI 知道每個額度還剩多少、多久重置、本地模型有沒有空，所以可以替你決定：

```sh
$(computai --pick) "幫我整理這個 PR"              # 跑 claude、codex 或本地模型
computai --pick --task light                      # 輕量任務可以丟給本地模型
computai --pick --json                            # 工具、指令、理由和完整排序
```

stdout 只有指令（`claude`、`codex`、`ollama run 模型`，別台機器上的是 `ssh 主機 ollama run 模型`），
一行理由印在 stderr。規則照順序：

1. 快重置（剩不到 1 小時，或週期的最後 15 %）而且還剩 ≥ 20 % 的額度：現在用掉，重置後就浪費了。
2. 輕量任務：本地的 Ollama 模型，不花額度。
3. 剩最多、照目前速度不會提早用完的訂閱。
4. 會提早用完的訂閱。
5. 已安裝 CLI、但額度不明的訂閱，作為備用選項。理由會明確說「額度不明」，不會當成剩 100%。
6. 重的任務最後才退到本地模型。用完的額度永遠不選。

只讀帳本（不連網、不 SSH），放在 `$(...)` 裡也夠快。首頁的建議也會在額度快重置又還剩很多時提醒；
agent 可以透過 MCP 的 `pick` 工具問同一個問題。

## 額度護欄（Claude Code 和 Codex 的 hook）

可選的 hook，讓 agent 自己知道額度或預算快用完了。`computai --setup` 會問要不要裝，裝之前先顯示 `settings.json` 的 diff。

- **PreToolUse**（只在派 subagent 時，`Task|Agent`）和 **Stop**：額度剩不到 `[guard] warn_left` %（預設 10），
  或這個月預估超過 `[budget] monthly_usd` 時，提醒 agent（「少派、派小一點的 subagent」），你也會看到訊息。
- `[guard] strict = yes`：這種時候直接擋下新的 subagent，並告訴 agent 原因。
- 絕不回「allow」，你自己的權限設定照常運作。出任何錯（沒有帳本、狀態太舊或壞掉）一律安靜放行。
- 很快：每次同步會把一小份護欄狀態寫進帳本，hook 跑的是產生在資料夾裡的小腳本（`claude-hook.py`），
  只讀那一列，大約 20 ms。不連網、不讀 prompt。`computai --hook claude-pretool|claude-stop` 給一樣的答案，只是比較慢。
- Codex 用同樣的 hook（`~/.codex/hooks.json`，派 subagent 的工具是 `spawn_agent`）。Codex 的新 hook 要先信任一次才會跑：
  打開 `codex` 輸入 `/hooks`。

## MCP server（給 agent 用）

`computai --mcp` 在標準輸入輸出上說 Model Context Protocol，讓 agent 在做花錢的事之前自己查預算。
工具有：`usage_summary`（某個月每個來源、每個模型的花費）、`limits`（額度）、`budget`（月底預估和今天）、
`machines`（GPU 使用率、載入的模型、還放得下多大的模型）、`advice`（建議）、`pick`（這個子任務該丟給誰，見上一節）。全部唯讀。
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
- *看不到 Claude 的百分比*：確認 `claude` 程式裝好並登入（限 Pro／Max），跑 `computai --claude-limits` 試試。
- *機器一直沒出現*：`--sample`、`--live`、`--web` 會顯示原因（「cannot read: ...」）。執行
  `ssh -o BatchMode=yes 主機 true`，必須不經提示就成功。「Host key verification failed」表示 known_hosts
  裡這台的 key 記在別的名字下：改用你平常 ssh 用的名字或 IP（Tailscale 的機器常常是 100.x 的位址），
  或先手動 `ssh 主機` 一次。
- *「ignoring secrets.ini」*：`chmod 600 ~/.config/computai/secrets.ini`。
- *Tailscale 在線，但 SSH 一直逾時*：若錯誤是 `Tailscale SSH requires an additional check`，
  在終端執行 `ssh 帳號@主機`，開啟它印出的驗證網址並登入。
  Tailscale 的 [SSH check mode](https://tailscale.com/docs/features/tailscale-ssh) 會在驗證期限到期後再次要求登入；
  `BatchMode=yes` 無法代替你完成瀏覽器驗證。完成後 ComputAI 下次取樣會重試。
  儀表板裡每台斷線機器只計算一次，舊取樣不算在線。
- *回報問題*：貼上 `computai --doctor --redact` 的輸出。機器名、SSH 主機、IP、專案名、家目錄底下的路徑、email
  和使用者名稱都會換成代號（`machine-1`、`ip-1`、`~/path-1`）。
- *新版*：有新版時 `computai --doctor` 和互動指令結束時會說（一天最多查一次；`[general] update_check = no` 關掉）。
  再跑一次安裝腳本就會更新。
- *想重來*：刪掉 `ledger.sqlite`，下次執行會重新匯入 log。
- *移除*：刪掉 `computai` 檔案、`~/.config/computai` 和 `~/.local/share/computai`。


## Token 細項與本地請求追蹤（beta.3）

```sh
computai --tokens --lang zh
computai --tokens --month 2026-10 --json
computai --proxy --tag test
# 讓自己的測試程式改呼叫 127.0.0.1:11435，再開另一個終端查詢：
computai --local-requests --lang zh
computai --local-requests 50 --machine m1m --model qwen3:8b --tag test --json
```

`--tokens` 預設最近 30 天（含今天），與預設卡片相同；指定 `--month`／`--since`／`--until` 則改用該區間。
列出精確整數、占總數百分比、來源／模型／專案前五名。總數 = 新輸入 + 快取讀取 + 5m／1h 快取寫入 + 輸出；
reasoning 已含於 output，只列子集合。B 是十億（10 億），M 是百萬；每次重複讀快取都計數，不能當成不同文字的數量。
快取讀取占總數與「輸入快取命中率」分母不同。雲端 GPU 的帳目不含 token，排除於此總數。
網頁 AI 用量頁可展開細項，TUI 花費頁顯示查詢入口；SVG 卡片附快取占比、輸出及可存取的詳細說明，仍不公開專案／機器名稱。

`--local-requests [N]` 預設今天最新 20 筆、最多 200，支援與 `--local-history` 相同的日期／機器／模型篩選。
`--tag` 可標記新 proxy 請求或篩選查詢：test、production、benchmark，未指定則沒有標籤。
時間是開始轉送的時間；耗時從轉送上游開始至轉送完成，包含連線、排隊、輸入處理、生成與傳輸。
輸出 tok/s = 輸出 token / 全程耗時，**不是純生成速度或首 token 延遲**。失敗或沒有用量時速度／token 顯示 `?`。
結果分成功、HTTP 錯誤、上游失敗、用戶端斷線、未回報用量；只依 HTTP／傳輸與用量欄位判斷，沒有檢查生成內容是否滿足任務。

只記錄新版 proxy 的五種生成 endpoint；不存 query、header、提示詞、回應或錯誤內文。
請求 metadata 獨立保存，不再加進 usage；自動改由服務計數器記帳時仍可保留逐筆紀錄，避免重複計算。
明確 `--no-ledger` 同時停用逐筆用量及請求 metadata，只保留記憶體 `/metrics`。
`--local-history` 繼續顯示原本的請求／取樣差值；舊紀錄無法補出耗時、結果與標籤。
TUI 本地頁有紀錄時優先顯示請求，網頁同時保留兩種表格。既有 proxy／TUI／web 需要重啟才能載入新版。
這些功能自 beta.3 提供。
