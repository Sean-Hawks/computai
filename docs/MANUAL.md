# ComputAI manual

ComputAI keeps one ledger (a SQLite file) of everything that costs you compute or AI money and
reports on it. This manual covers setup, every command, the configuration files and how the
numbers are worked out. 中文版：[MANUAL.zh-TW.md](MANUAL.zh-TW.md).

- [Where things live](#where-things-live)
- [Subscriptions: Claude Code and Codex](#subscriptions-claude-code-and-codex)
- [Commands](#commands)
- [Configuration](#configuration)
- [Machines and local models](#machines-and-local-models)
- [The token-counting proxy](#the-token-counting-proxy)
- [Cloud GPUs](#cloud-gpus)
- [Organisation API usage](#organisation-api-usage)
- [Analysis](#analysis)
- [Dashboards](#dashboards)
- [How the numbers are worked out](#how-the-numbers-are-worked-out)
- [Troubleshooting](#troubleshooting)

## Getting set up

`computai --setup` walks through everything below one question at a time and writes `config.ini` only
after you confirm (the previous file is kept as `config.ini.bak`). `computai --doctor` checks every source
and machine and prints the command that fixes each gap. `computai --set SECTION.KEY=VALUE` and
`--unset SECTION.KEY` change single settings without touching your comments. `computai --discover --add`
adds every reachable machine with power settings suggested from its hardware.

In beta.3, `computai` first shows a menu with six choices. Enter opens the monitor;
`2` makes a monthly recap, `3` opens the browser automatically, `4` analyzes spending, `5` checks sources and
`6` sets up your environment. `0`, `q`, Ctrl-C or EOF exits. Browsing the menu does not read usage, connect
to machines or create configuration/ledger files. Outside a terminal, it prints the same guide and exits.
Use `--summary` or `--json` to get usage in scripts. Before beta.3, bare `computai` opened the monitor directly.

Selecting the monitor from the menu skips plan questions. The first direct `computai --live` with no plan set
asks one question per subscription:
the plan in Codex's logs, or for Claude a guess from the last 30 days of usage. Enter keeps it, `n` skips,
or type another plan's name. It only asks once; `computai --setup` changes it later.

## Where things live

| What | Default | Override |
|---|---|---|
| Settings (`config.ini`, `prices.ini`, `secrets.ini`) | `~/.config/computai/` (Windows: `%APPDATA%\computai`) | `COMPUTAI_CONFIG_DIR`, `XDG_CONFIG_HOME` |
| Ledger (`ledger.sqlite`) | `~/.local/share/computai/` (Windows: `%LOCALAPPDATA%\computai`) | `COMPUTAI_DATA_DIR`, `XDG_DATA_HOME` |
| Claude Code logs | `~/.claude/projects/` and `~/.config/claude/projects/` | `CLAUDE_CONFIG_DIR` (comma-separated list allowed) |
| Codex logs | `~/.codex/sessions/`, `~/.codex/archived_sessions/` | `CODEX_HOME` |

`computai --paths` prints the first two. The first run creates `config.ini` and `prices.ini`
from templates; after that ComputAI only reads them, so your edits stay. Deleting the ledger
is safe: the next `--sync` rebuilds subscription history from the logs (machine samples and
cloud history are lost).

## Subscriptions: Claude Code and Codex

Nothing to set up. `computai --sync` (and every report, which syncs first unless you pass
`--no-sync`) reads new log lines. Only files that changed since the last sync are re-read.

- **Claude Code**: one row per API response, deduplicated by message id and request id.
  Claude Code writes the same response several times while it streams; ComputAI keeps the
  most complete copy. Cache writes are split into 5-minute and 1-hour, thinking tokens are
  recorded separately (they are part of output), subagent requests are marked, and the
  working directory is the project.
- **Codex**: one row per `token_count` event. OpenAI counts cached tokens inside
  `input_tokens`; ComputAI stores uncached input so both providers mean the same thing.
  The totals match Codex's own `tokens_used` per thread.
- **Limits**: both are read for the whole account (other machines, T3 Code, claude.ai and other people
  count too). How often follows how fast they burn:
  - Every `poll_minutes` (default 10) while nothing is close to running out; faster while a limit burns,
    down to once a minute (remaining % ÷ burn rate ÷ 4). Speeding up takes effect at once; slowing down
    relaxes gradually so a short pause doesn't drop back to the slow pace.
  - 30 seconds after any window resets, one extra check, so the recovery shows right away.
  - The burn rate comes from the ledger's own samples of each window. `computai --doctor` shows the next
    check and why (`weekly limit runs out in 3h00m at this pace: every 45m`); `[limits] refresh = fixed`
    goes back to a fixed `poll_minutes`.
  - Claude: ask the official `claude` CLI (`claude -p /usage`, a local command that calls no model and uses
    no quota); Pro and Max accounts only. Setting Claude Code's status line to `computai --statusline`
    (see [one-line.md](one-line.md)) also works and updates on every reply.
  - Codex: ask the official `codex` CLI (`codex app-server`); the limit windows in its logs are read too.
  - The official CLIs handle their own login; ComputAI only receives percentages and reset times.
    `[claude]` / `[codex] poll_minutes = 0` turns it off.

### More agents: Gemini CLI, OpenCode, Cursor

Read the same way, usage fields only:

- **Gemini CLI**: `~/.gemini/tmp/<project>/chats/*.jsonl` (`GEMINI_CLI_HOME` moves it). One row per Gemini reply, deduplicated by
  its id; `input` includes cached tokens and `output` excludes thinking, so ComputAI subtracts and adds them (checked on
  real recordings: total = input + output + thoughts + tool). Subagents (`kind: subagent`) count under their session.
- **OpenCode**: `~/.local/share/opencode/opencode*.db` (and the older `storage/message/*.json`). Only assistant message
  metadata is read through a read-only connection, including committed WAL updates. The database containing conversations
  is never copied, and the `part` table is never queried. Input,
  output, reasoning and cache are separate in OpenCode, and child sessions count as subagents. OpenCode's own cost is
  used when it has one.
- **Cursor** keeps no log on your computer. Export your usage from cursor.com/dashboard (Usage, Export CSV) and run
  `computai --import-cursor FILE`, or set `[cursor] exports = ~/Downloads/usage-events*.csv` to import on every sync.
  Columns are matched by name; the format was taken from a third-party parser and has not been checked against a
  real export yet. Rows marked "Errored, No Charge" are skipped; importing overlapping exports never counts a row twice.

## Commands

All commands accept `--json`. Ranges: `--month [YYYY-MM]`, `--since YYYY-MM-DD`,
`--until YYYY-MM-DD` (inclusive); the default is this month.

| Command | What it does |
|---|---|
| `computai` | Feature menu; Enter opens the monitor. Outside an interactive terminal: guide, then exit. |
| `--summary [--by model\|project\|session\|day]` | Totals per source and model, API-equivalent cost, plan comparison, limits, machines, cloud and alerts. |
| `--sync` | Import new usage and print how many rows were added per source. |
| `--line [--sep " · "]` | One line: each subscription's fullest limit window and today's cost. Re-reads logs at most every 30 s. |
| `--statusline` | For Claude Code's `statusLine`: records native limits and displays model, context and last request; `--statusline-view compact` keeps one line. |
| `--live [-n SEC]` | Live terminal dashboard: one panel per machine (bars and sparklines for CPU, memory, every GPU and power, plus its inference servers), AI usage with limit bars and 14-day cost trends, and alerts. Two columns on wide terminals, one line per machine when the window is short. `q` quits. |
| `--once` | Print the live dashboard once and exit (reads logs and samples machines first). |
| `--card --setup` | Set up the GitHub profile card in a few questions (finds or clones the profile repo, writes the first card, adds it to the README). |
| `--watch` | No screen: keep the ledger fresh and send notifications (see Notifications). |
| `--claude-limits` | Read the Claude account's limits now through the claude CLI (`claude -p /usage`; no model call). |
| `--codex-limits` | Read the Codex account's limits now through the codex CLI (includes other machines and people on the account). |
| `--limit-reset claude\|codex` | Mark a subscription's limits as reset now (after an early reset the logs can't show); the next real reading replaces it. |
| `--notify-test` | Send a test notification. |
| `--install-watch` / `--uninstall-watch` | Start `--watch` automatically at login, or stop doing so. |
| `--bench [--machine NAME]` | Run each local model for a few seconds: tokens/s, watts, J/token, electricity per 1M tokens versus the API. |
| `--theme cyber\|classic` | Calm dark cyberpunk instrument (default, see [DESIGN.md](DESIGN.md)) or the slurmtop look, for the terminal, web, report and recap (or `[general] theme`). |
| `--lang zh` | Traditional Chinese for the live and web dashboards and `--line` (or `[general] lang = zh`). The default `lang = auto` follows the system language; on macOS it uses the system's preferred language, because terminals such as cmux and Ghostty set `LANG=en_US` regardless. `COMPUTAI_LANG=en` or `lang = en` forces English. |
| `--web [[HOST:]PORT]` | Browser dashboard (phone layout), `/api/state` JSON and `/metrics` for Prometheus. Default `127.0.0.1:8765`. |
| `--recap [YEAR] [--html FILE]` | A year in review (tokens, value, active days, streak, busiest day, favourite models, local inference); the HTML card leaves out project and machine names so it can be shared. Plan fees are counted for each month with usage, at today's `[plans]` prices. |
| `--wrapped [YYYY-MM\|YYYY] [--html FILE] [--svg FILE]` | Spotify-Wrapped-style recap of a month (default: this month so far) or a year: terminal text, a story page (`--html`) and a 1200x630 share card (`--svg`). Aggregates and model names only. See Wrapped. |
| `--card [--period 30d\|month\|year\|all] [--card-theme dark\|light] [--svg FILE] [--publish PATH [--push]]` | Small SVG card for a GitHub profile README. See Profile card. |
| `--weekly [--send]` | The last 7 days in a few lines; `--send` posts it to `DISCORD_WEBHOOK_URL` and/or Telegram (`TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`), read like other secrets. Run it from cron for a weekly message. |
| `--totals FILE [--who NAME]` / `--lab DIR` | Lab mode: everyone writes their month's totals (cost and tokens per source and model, kWh; no project names) to a shared folder, and `--lab` combines the folder into one table. |
| `--csv FILE` | Every usage record in the range (time, source, model, project, tokens, cost) as CSV; text starting with `= + - @` is prefixed with `'` so spreadsheets don't run it. |
| `--report [--html FILE]` | Monthly report as text, or a self-contained HTML page with a daily cost chart. |
| `--analyze` | Month-end forecast, plan check, cache efficiency, energy. |
| `--payback USD [--gpu-watts W --hours-per-day H --rent-per-hour USD]` | How long a GPU takes to pay for itself versus renting. |
| `--discover` | Look for machines in `~/.ssh/config` and on Tailscale, try SSH to each, explain failures and print `[machines]` lines to paste. |
| `--wake NAME` | Send a Wake-on-LAN packet to a machine that has `mac = ...` (and optionally `wol_address = ...`) in its `[machine.NAME]` section. |
| `--sample` | Read every machine once and print the machine table. |
| `--cloud` | List RunPod, Vast.ai and Lambda instances and record their cost. |
| `--proxy [--listen ... --upstream ... --machine NAME]` | Token-counting proxy for Ollama and OpenAI-compatible servers. |
| `--tokens` | Exact token breakdown and cache share for the last 30 days; date filters and JSON supported. Beta.3. |
| `--local-requests [N] [--tag test/production/benchmark]` | New proxy request timings, HTTP outcomes and output / elapsed tok/s; date/machine/model filters. Beta.3. |
| `--local-history [N] [--machine NAME] [--model MODEL]` | Recent local usage: today's latest 20 rows by default, at most 200; date filters and `--json` supported. Added in beta.3. |
| `--mcp` | MCP server on stdio for agents (see below). |
| `--paths`, `--version` | |

`--live`, `--web` and `--proxy` keep running; while they do they re-read logs every 30 s,
sample machines every `--sample-every` seconds (default 60) and, if keys are set, cloud
providers every 5 minutes.

## Configuration

`config.ini` (comments start with `#`):

```ini
[general]
usd_to_local = 32        ; exchange rate, used when electricity is priced in another currency
local_currency = TWD

[plans]                  ; <source> = <plan name>, <USD per month>, <date checked>
claude = Claude Max 5x, 100, 2026-10-03
codex = ChatGPT Pro, 200, 2026-10-03

[plan_options]           ; for the plan simulator: <name> <USD> x<allowance>
claude = Pro 20 x1, Max 5x 100 x5, Max 20x 200 x20
codex = Plus 20 x1, Pro 200 x20

[machines]               ; <name> = local | <ssh host>
this-computer = local
gpubox = gpubox.tailnet

[machine.gpubox]
services = ollama:11434, vllm:8000
base_watts = 80          ; rest of the machine, on top of measured GPU power
cpu_watts = 90           ; extra power at 100% CPU, scaled by CPU use (CPU inference, builds)
plug = shelly:192.168.1.50  ; measured power from a smart plug: shelly, shelly1 (Gen1), tasmota,
                         ; or ha:sensor.x (Home Assistant, with HA_URL and HA_TOKEN secrets)
[machine.this-computer]
idle_watts = 6           ; when GPU power can't be read (Macs): interpolate idle..max by load
max_watts = 30

[power]
price_per_kwh = 0.15
currency = USD
tariff = flat            ; or tou, see below
idle_alert_minutes = 15  ; model loaded but unused this long -> alert

[budget]
monthly_usd = 0          ; 0 = off

[cloud]
idle_gpu_util = 5        ; % below which a billing GPU counts as idle
idle_alert_minutes = 20
ssh_user =               ; read GPU use over SSH when the API has none (Lambda)
```

`prices.ini` holds API prices per million tokens (`input`, `output`, `cache_read`,
`cache_write_5m`, `cache_write_1h`, plus `checked` and `source`). A model without its own
section uses the longest section name that is a prefix of it, so `[claude-sonnet-5]` covers
`claude-sonnet-5-5`. Fast mode is priced as `<model>@fast`. Models with no price are listed at
the bottom of `--summary`; add a section for them.

`secrets.ini` (must be `chmod 600`, otherwise it is ignored with a warning):

```ini
[secrets]
RUNPOD_API_KEY = ...
VAST_API_KEY = ...
LAMBDA_API_KEY = ...
ANTHROPIC_ADMIN_KEY = ...
OPENAI_ADMIN_KEY = ...
```

Environment variables with the same names take precedence.

### Time-of-use electricity

Set `tariff = tou` under `[power]`. The `tou_*` keys describe the tariff in local time at
`tou_utc_offset`: which months are summer, the peak hours for summer and the rest of the year,
the four prices, and whether weekends are off-peak all day. The defaults are Taipower's
residential two-tier plan (簡易型時間電價 二段式); they could not be checked against
taipower.com.tw, so compare them with your bill. With a time-of-use tariff, energy is priced by
the time it was used, and `--analyze` shows how much AI work ran at peak and what moving it
off-peak would save.

## Your other computers

Limits are account-wide, but tokens and cost come from this computer's logs. To add your laptop, work
computer or homelab boxes ([details](MULTI-DEVICE.md)):

- **Shared folder** (recommended): on every computer, `computai --set devices.folder=PATH` with a folder they all
  sync (iCloud Drive, Dropbox, Syncthing, a private git repo). Each writes its own usage there (usage numbers only:
  no prompts or full paths; session IDs are replaced by device- and source-scoped one-way hashes) and reads the others'.
  `devices.name` sets the name shown. The anonymous-session export fix is available in released beta.2 and this checkout;
  see the [upgrade steps](MULTI-DEVICE.md#從沒有-session-的舊格式升級) to recover grouping for previously imported usage.
- **SSH pull**: `[machine.X] usage = pull` for a machine in `[machines]`. ComputAI copies itself to
  `~/.cache/computai` there (only `python3` is needed) and runs `computai --export-usage`.

Each row is counted once however it arrives. A broken file is skipped whole and earlier numbers stay. Devices
that have not reported for 10 minutes are marked stale. `--summary` lists devices, `--summary --by device`
splits by device, and `--doctor` shows each device's last report and any errors.

## Machines and local models

`computai --discover` lists candidates from `~/.ssh/config` and Tailscale, tests SSH to each and
prints the lines to add. Each machine in `[machines]` is read with one `ssh` call that runs a POSIX `sh` script (or
locally, for `local`). Requirements on the machine: `sh`, and `curl` or `wget` to look at
inference servers. Use key-based SSH that works without a prompt (`ssh -o BatchMode=yes host true`
must succeed); a machine that does not answer within 25 seconds is skipped for that round.

What is read: CPU use, memory, NVIDIA GPUs (`nvidia-smi`), AMD GPUs (sysfs), Apple GPUs
(`ioreg`), and these inference servers on the machine's own loopback:

| Service | Default port | Read from |
|---|---|---|
| Ollama | 11434 | `/api/ps`: loaded models and their memory |
| llama.cpp (`--metrics`) | 8080 | `/metrics`: prompt and generated tokens, requests in flight |
| vLLM | 8000 | `/metrics` |
| SGLang (`--enable-metrics`) | 30000 | `/metrics` |
| LM Studio | 1234 | `/api/v0/models`: loaded models |
| other OpenAI-compatible (MLX, ...) | set it | `/v1/models` |

Set `services = kind:port, ...` per machine to change the list. Token counters that grow
between two samples become `local` usage rows (cost $0; their cost is the electricity).
Ollama has no metrics, so its tokens need the proxy, but ComputAI still notices Ollama
activity: every request pushes the model's `expires_at` forward.

**Alerts**: a model that stays loaded with no activity for `idle_alert_minutes` raises
"loaded but idle (holding N MB)".

## The token-counting proxy

```sh
computai --proxy                                   # 127.0.0.1:11435 -> http://127.0.0.1:11434
OLLAMA_HOST=127.0.0.1:11435 ollama run qwen3:0.6b  # point clients at the proxy
```

The proxy forwards everything unchanged and reads only the usage fields in responses
(Ollama's `prompt_eval_count` / `eval_count`, OpenAI's `usage`, the Responses API's
`response.usage`). Streaming OpenAI requests that did not ask for usage get
`stream_options.include_usage` added, because otherwise the stream contains no token counts;
turn that off with `--no-usage-injection`. Tokens are booked to `--machine` (default: the first
`local` machine). Listening on anything other than loopback prints a warning: anyone who can
reach the port can use your models.

## Cloud GPUs

Set one or more of `RUNPOD_API_KEY`, `VAST_API_KEY`, `LAMBDA_API_KEY` and run `computai --cloud`
(or keep `--live`/`--web` running). Only read-only "list my instances" calls are made.

- RunPod: status, price and GPU from the REST API; GPU use from the GraphQL API.
- Vast.ai: status, `dph_total`, GPU use; stopped instances keep paying `storage_cost`.
- Lambda: status and price; no GPU use in the API, so set `[cloud] ssh_user` (usually `ubuntu`)
  to read `nvidia-smi` over SSH.

Each check stores a snapshot; the time between two snapshots is charged at the hourly price
(gaps over 6 hours are not guessed). **Idle but billing**: a GPU under `idle_gpu_util` % for
`idle_alert_minutes` raises an alert with the money spent so far while idle.

## Organisation API usage

With `ANTHROPIC_ADMIN_KEY` (`sk-ant-admin...`) or `OPENAI_ADMIN_KEY`, `--sync` also imports the
organisation's daily usage per model from the admin usage APIs (31 days the first time, then
from the day before the last sync). Subscription usage (Pro, Max, Plus) is never in these APIs.

## Analysis

`computai --analyze` (uses the chosen range for the cache report, the current month for the rest):

- **Month-end forecast**: subscription fees + money already spent this month (cloud, API,
  electricity) + the last 7 days' daily average for the rest of the month. Also what each
  subscription's usage would cost at API prices at the current pace. `[budget] monthly_usd`
  turns on an over-budget alert.
- **Plan check**: the highest limit-window use in the last 30 days, scaled by the plans'
  allowance multipliers, picks the cheapest plan that would have stayed under 90 %. If the
  API-equivalent cost is below the cheapest plan, it says pay-as-you-go would be cheaper.
- **Cache efficiency**: within a session and model, a request that writes at least half of its
  context to the cache again is a rewrite. The waste is the difference between cache-write and
  cache-read prices for those tokens. Rewrites after a pause longer than the cache lifetime
  (5 minutes or 1 hour) are counted separately: those come from leaving a session idle.
- **Energy**: electricity cost per million locally generated tokens, and off-peak savings.

`computai --payback 1800 --gpu-watts 450 --hours-per-day 8` compares buying a GPU with renting:
the rent comes from `--rent-per-hour` or, if omitted, your cloud history (per GPU). With a
time-of-use tariff it assumes the work is scheduled off-peak where possible.

## Dashboards

- `--live` (or Enter in the menu, cyber theme) has tabs: **1 overview** (fits one screen: limit gauges, one line per machine, spend, the top alerts and advice), **2 limits**, **3 machines**, **4 local models**, **5 spend**, **6 timeline**; `1`-`6` or `Tab` switch, `q` quits. `h` or `?` opens help with feature commands, even while data loads; `h`, `?` or Esc returns, `c` opens the card creator. Limits show what is left by default (`[general] limits = used` flips it). The panels, top to bottom:
  - **Verdict**: ALL CLEAR, WATCH or ALERT and the worst problem in plain words
    ("Codex weekly limit is used up - resets in 4h43m · +1 more").
  - **LIMITS**: a thick gauge per limit window with its percentage. A white `┃` marks how much of the
    window has passed, so a bar beyond it is burning faster than time. Under it: "at this pace it runs out
    in 1h20m" or "about 65% by the reset". A subscription with usage but no limit data says how to connect it.
  - **COMPUTE**: a panel per machine (CPU, memory, each GPU, power, inference servers and their models).
    Its data source and age are on the bottom border.
  - **AI subscriptions & spend**: value at API prices versus the monthly fee, and what you actually pay.
  - **ALERTS** and **ADVICE**.

  It refreshes every `-n` seconds. `--once` prints it once; it falls back to ASCII when the terminal
  can't draw block characters.
- `--web`: open `http://127.0.0.1:8765/`. `--web 0.0.0.0:8765` exposes your usage, project names and
  machines to the network and prints a warning; to see it from a phone or another computer, use one of these instead.
  - `computai --web --tailscale` (or just `computai --tailscale`): the server stays on 127.0.0.1 and
    `tailscale serve` forwards it over HTTPS to your tailnet only. It prints a link like
    `https://my-mac.tail1234.ts.net/` and turns the forwarding off when it stops (Ctrl-C, closing the
    terminal, or the service stopping). It never takes over a port another `tailscale serve` already uses:
    if 443 is taken it uses 8443 or 10000. Without Tailscale it says how to install it and does not fall back
    to `0.0.0.0`. `computai --install-watch --tailscale` keeps it running in the background (the service runs
    `--web --tailscale`, which also keeps the ledger fresh and sends notifications).
  - An SSH tunnel: `ssh -L 8765:127.0.0.1:8765 host`.
  - *Cloudflare Tunnel (not built in yet; planned as an advanced option)*: a public hostname reaches
    anyone on the internet, so ComputAI will only open one when the hostname is behind
    [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/) (an identity check
    before any request reaches you), and will refuse with that reason otherwise. If you set one up by hand, put
    an Access policy in front of it first and point the tunnel at `http://127.0.0.1:8765`.
- The web page follows the terminal overview: verdict, limits, four tiles (today vs yesterday, this month with each
  plan's payback and what you will pay, local inference speed, power with a trend line), then a machine table, a
  usage-mix donut and "needs attention" (alerts first, then advice), with the detailed panels below. Everything
  comes from the same `dashboard_state()` as the terminal. It has a web manifest and icons, so on a phone opened
  through `--tailscale` you can "Add to Home Screen" and it opens like an app.
- `/metrics`: gauges prefixed `computai_` (month cost and tokens per source, limit use, machine
  CPU/GPU/power, cloud price and GPU use, forecast, alerts by kind).
- `--report --html FILE`: a single HTML file you can keep or send.

## Notifications

ComputAI tells you when something changes, once per change:

- a limit reaches 80%, with when it runs out at this pace;
- a limit runs out, and how much the other subscription has left;
- **a limit resets and you can use it again**;
- a machine stops answering, a model holds memory unused, or a cloud GPU idles while billing;
- the month goes over budget.

Notifications run inside `computai`, `--web` and `--watch`. The state lives in the ledger, so restarting
or running several copies does not repeat anything. The first run only records how things are.

- `[notify] desktop = yes` (default) uses macOS Notification Center, `notify-send` on Linux, or a
  Windows balloon.
- `[notify] chat = yes` also posts to Discord / Telegram (`DISCORD_WEBHOOK_URL`,
  `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`).
- `computai --notify-test` sends one to check.
- `computai --install-watch` starts `--watch` at login: launchd on macOS, `systemd --user` on Linux,
  Task Scheduler on Windows. `--uninstall-watch` removes it.

## Local models panel

The LOCAL MODELS panel (terminal and web) lists every model per machine:

- whether it is generating, and its tokens per second now;
- tokens today and this month;
- what those tokens would cost at an API price. That price comes from `[local] compare_model`, or else the cheapest model in `prices.ini`.

vLLM, llama.cpp and SGLang report token totals themselves. Ollama does not: put the token-counting proxy in front of it.

1. Move Ollama to another port: `OLLAMA_HOST=127.0.0.1:11436 ollama serve`.
2. Start the proxy on the old port: `computai --proxy --listen 127.0.0.1:11434 --upstream http://127.0.0.1:11436 --machine NAME`.

Clients keep using `:11434` unchanged. The proxy serves running totals at `/metrics`, which sampling reads over SSH, so this works on other machines too.

- If sampling reads the proxy as an Ollama service, or reads counters from upstream vLLM/llama.cpp/SGLang, the proxy only keeps totals. Sampling native Ollama/LM Studio alone does not disable per-request recording.
- Sampling is normally detected automatically to avoid double counting. Explicit `--no-ledger` keeps only `/metrics`; in beta.3 it also disables persistent request metadata.

## GitHub profile card, kept fresh

The quickest way is `computai --card --setup`; the README has the full guide (what each part means, styles, privacy, troubleshooting). `computai --doctor` shows whether the card is set up and when it was last written. The manual way:

Set these in `config.ini`:

```ini
[card]
repo = ~/path/to/your-profile-repo/assets
push = yes
```

Once a day, `computai`, `--web` or `--watch` rewrites the two card SVGs there and commits them.

- `style` picks the look: `netrunner` (default), `arasaka`, `militech`, `amber`, `matrix` or `synthwave`. `colors = #from, #to` sets your own gradient.
- Beta.3 also adds `minimal`, `paper`, `github` and `terminal`: a monochrome banner, paper portrait, statistic dashboard and plain console.
- `layout = auto` follows the style; choose `hud`, `compact`, `dashboard` or `portrait`, or override with `--card-layout`. Existing styles and the `mono`/`computai` aliases retain the HUD.
- `computai --card --html styles.html` writes a local comparison of ten styles, both themes and four layouts, with SVG commands. The gallery uses preset colours; individual SVGs and daily updates use your settings.
- `handle` sets the title; it defaults to the repo's GitHub account.
- `lang` sets the card's language.
- `--setup` asks for all of this and finds the profile repo on disk. Before pushing it rebases onto any commit a bot pushed in the meantime.

## Recent local inference (beta.3)

Available since `v0.1.0-beta.3`.

```sh
computai --local-history
computai --local-history 50 --machine m1m --model qwen3:8b
computai --local-history 200 --since 2026-10-01 --until 2026-10-04 --json
```

Rows show time, model, machine, input (including cache reads), output and recording source.
Proxy rows represent requests and show their count. Counter rows represent usage between two samples;
their request count is unknown (`-`) and a row may cover multiple requests. This reads the existing ledger
without importing logs or running a model. Capture through the proxy or service `/metrics` first;
uncaptured history cannot be recovered.

Terminal tab **4 Local models** and the web dashboard show today's latest eight rows. Short terminals
show fewer rows with a CLI hint. Restart an existing dashboard to load the new code.
Only usage metadata is recorded: no prompts, responses, Claude Code task contents, duration or outcome.

## What local models really cost (`--local-cost`)

`computai --local-cost [--month]` puts each local model next to small cloud models:

- **Electricity per 1M tokens**, from the machine's measured AI energy split over its models' tokens; a model
  with no measured usage uses its latest `--bench` result instead (marked "from --bench").
- **Hardware** (optional): `[local] hardware_usd` and `lifetime_years` add depreciation per 1M tokens and a
  break-even: how many tokens a month the hardware needs to beat each API model.
- **vs**: how many times cheaper than each model in `[local] compare_models` (default `claude-haiku-4,
  gpt-5.4-mini`, mixing input and output price half and half). A compare model needs an exact section in
  prices.ini; otherwise it says so instead of guessing from a similar name.
- **Routing**: if this month's light Claude and Codex requests (output ≤ `light_output`, context ≤
  `light_context`) had gone to your cheapest local model, the money (at API prices) and share of subscription
  usage saved, and the electricity it would cost.
- **Carbon**: kWh × `[energy] grid_kg_per_kwh`. The default is Taiwan's 2024 electricity emission factor,
  0.474 kg CO2e/kWh (Energy Administration, MOEA, published 2025-04-14); set your own grid's factor or 0.

The local models tab and Wrapped carry the one-line version: "This month local models saved you $17 and used
0.6 kWh".

## Local model benchmark

`computai --bench [--machine NAME]` sends the same fixed prompt to every running inference server for a
few seconds. It measures tokens per second, samples the machine's power while it generates, and works
out joules per token and the electricity per million tokens. It compares that with the cheapest output
price in `prices.ini`; hardware is not counted. Only usage fields are read from the answers.

Macs need `idle_watts` / `max_watts` (or a smart plug) for the power columns.

## Personal history profile (beta.3)

```sh
computai --profile --html profile.html --who hawks
computai --profile 2026-09 --html september.html
computai --profile 2026 --html annual.html --no-sync
computai --profile --json --no-sync
```

The self-contained page offers an all-time profile, monthly and annual reports, light/dark themes and
browser printing. JavaScript-free readers see every period. Daily bars preserve calendar gaps; mobile
readers can scroll the chart and expand an exact-count table. Monthly rows link to their reports.

Active days count positive tokens, including zero-cost local inference. Total adds uncached input,
cache reads, both cache-write buckets and output; it excludes reasoning already within output and GPU
rental rows. Model/source shares use total tokens, with the top five models shown. Cache reads / total
and cache reads / input have different denominators.

Source coverage lists first/latest records and record counts, not request counts. Counter samples may
span multiple requests. In-progress and late-starting periods are marked; coverage does not guarantee
complete account history. Sources identify record formats, not GUI applications. Unavailable GUI or
remote history cannot be reconstructed, nor can tokens establish what you worked on or your ability.

API equivalents recalculate priced models using current `prices.ini` rates and list unpriced models.
They are not bills or historical subscription payments. By default only local Claude, Codex, Gemini,
OpenCode and saved Cursor usage is imported; no device/SSH or cloud API sync. Other token sources already
in the ledger still count. `--no-sync` skips imports. Both HTML and JSON include every observed period;
the date selects the initial HTML view, not an export filter. No prompts, responses, projects, machines
or sessions enter the profile, and nothing is uploaded automatically.

### One-page social cards

```sh
computai --profile --share-layout square --html share.html --svg share.svg --who hawks
computai --profile 2026-09 --share-layout portrait --html month-share.html --no-sync
computai --profile 2026 --share-layout wide --svg year-share.svg --no-sync
```

Use `computai recap` to find local usage, select a month and open the download page. Click Download PNG to share.
Use `computai recap 2026-09` for a month or `computai recap --help` for focused options; language follows settings or `--lang`.
Legacy `--create` remains supported; `--recap YEAR` retains its existing annual-report meaning.
The Web header and TUI `c` key open the same tool. `--no-open` writes it without launching a browser; `--no-sync` skips local imports.

Square is 1080×1080, portrait 1080×1350 and wide 1200×630. The default uses the calm Web/TUI design, independent of saved legacy card settings.
Explicit `--card-style amber` or another existing style selects the legacy HUD. Names use `--who` or saved card.handle; language follows --lang or general.lang.
Cards show dates/partial periods, total and exact tokens, cache share, output, active days, longest streak,
up to two sources plus Other, and the top model by tokens including cache. Portrait adds calendar-day or
monthly bars, marking in-progress months with *. Long histories show the last 12 recorded months.
There are no subscription-return, payment, ability or session claims.

SVG defaults to square. A share layout without a file prints SVG to stdout; --json still prints data.
HTML with either share option becomes a single-card preview with local original-size PNG and SVG downloads.
The canvas uses the SVG's native dimensions with no Python dependencies or network access. Without JavaScript,
viewing and SVG downloads still work. Share HTML/SVG include only the chosen period; plain profile HTML and
JSON retain all periods. Nothing is posted to social media automatically.

## Wrapped

`computai --wrapped [YYYY-MM|YYYY]` is the shareable version of the numbers: tokens, API-equivalent value,
how much your subscriptions paid back, active days and longest streak, busiest day and weekday, the hour you
work in most (local time) with a persona (night owl 0-4h, early bird 5-8h, nine to five 9-17h, evening hacker
18-23h), top 3 models by share of tokens, number of sessions and the size of the biggest one, what the prompt
cache saved (cache-read tokens x (input price - cache-read price)), local-model tokens and kWh, the change
against the previous equal period (a month still in progress is compared with the same number of days of the
month before), and fun equivalences from output tokens (0.75 words per token: copies of The Lord of the Rings
at 480,000 words, hours of reading at 250 words per minute; the constants are in `EQUIVALENTS` in the script).

- `--html FILE` writes a full-screen story page: progress bars, one big number per slide, click or tap
  (left third goes back), arrow keys or space, swipe on a phone, and a shareable summary card at the end.
  One file, no network, no external fonts; it respects `prefers-reduced-motion`. Open `FILE#5` to start at
  slide 5.
- `--svg FILE` writes a 1200x630 share card.
- `--json` prints the data (including the per-day values behind the charts).

Privacy: only aggregates and model names. Project names, paths, session ids, machine names and prompts are
never read into the page. Plan fees use today's `[plans]` prices times the months that had usage.

## Profile card

`computai --card --svg computai-card.svg` writes a 495x195 SVG in the style of github-readme-stats: tokens,
API-equivalent value, top model, active days and streak, and a 14-day bar chart (12 months for `year` and
`all`). `--period` picks the range: `30d` (default: the last 30 days, a rolling window so it is never empty on
the 1st), `month`, `year` or `all`. `--card-theme light` writes the light variant. It is plain SVG with inline
attributes, no scripts, no fonts, no images; all text is escaped. With neither `--svg` nor `--publish` the SVG
goes to stdout.

To show it on your GitHub profile, put the two files in your profile repo (the one named like your account):

```sh
computai --card --publish ~/Documents/you-profile-repo
git -C ~/Documents/you-profile-repo push      # or add --push to the command above
```

`--publish PATH` writes `computai-card.svg` and `computai-card-light.svg` into the git repository at PATH and
makes one commit with just those two files (nothing is committed when the cards did not change; other staged
files stay untouched). It prints each step it took. It never pushes unless you also give `--push`, which runs a
plain `git push` (so the branch needs an upstream). In the profile `README.md`:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="computai-card.svg">
  <source media="(prefers-color-scheme: light)" srcset="computai-card-light.svg">
  <img alt="ComputAI card" src="computai-card.svg" width="495">
</picture>
```

The card shows a snapshot; run the command again (for example from cron) to refresh it.

## Agent timeline

Tab 6 (and `computai --timeline`) draws the day's activity from timestamps and token counts only. The date,
snapshot time and hourly scale appear above numbered Claude/Codex sessions and explicitly labeled local models.
Remote sessions include `@laptop`, subagents sit below their parent, and `↶` marks continuation from yesterday.

- `━` shows estimated activity, `·` shows gaps between requests, `│` marks hours, and `┃` marks now.
- Wide terminals show accumulated activity and tokens on the right. A second line shows each row's first-to-last activity range; accumulated time excludes gaps.
- The summary separates Claude/Codex hours from local inference hours. Both add across rows, including concurrent sessions.
- Requests up to five minutes apart form a segment, with a one-minute minimum for isolated requests. This estimates activity rather than task content or exact runtime.
- The footer spells out peak concurrency, the longest stretch and longest gap. Cost peaks are API-equivalent estimates, rather than subscription payments.

It fits 60 columns, with durations below each row on narrow terminals. Short TUI screens use compact rows and
show how many sessions were omitted.

`computai --timeline --svg FILE` writes the same chart as an SVG without project or machine names (rows read
"Claude 1", "Codex 2" and local model names), and Wrapped shows the busiest day's timeline.

## Team leaderboard (`--team`)

An opt-in board for friends, with no server: everyone pushes a totals-only JSON file to one shared git repo
(a private repo, or a GitHub Gist, which is a git repo too).

```sh
git clone <your team's repo or gist> ~/team
computai --set team.repo=~/team --set team.handle=neo
computai --team publish      # shows the full JSON, asks, then commits and pushes computai-team-neo.json
computai --team              # git pull, then the board: tokens this week, change vs last week, agent hours,
                             # most agents at once, streak
computai --team leave        # deletes your file and pushes
```

The file holds only those four numbers for this week and last week, your handle and the time: no project
names, paths, models, machines, IPs or sessions. Other people's files are read with a strict schema (anything
else in them is ignored). The board also shows on the spend tab and as a Wrapped page.

## Which agent now (`--pick`)

ComputAI knows how much of each limit is left, when it resets and whether a local model is free, so it can
decide for you:

```sh
$(computai --pick) "tidy up this PR"              # runs claude, codex or a local model
computai --pick --task light                      # light tasks may go to a local model
computai --pick --json                            # tool, command, reason and the full ranking
```

stdout is only the command (`claude`, `codex`, `ollama run MODEL`, or `ssh HOST ollama run MODEL` for a model on
another machine); the one-line reason goes to stderr. The rules, in order:

1. A limit that resets soon (within an hour, or the last 15% of its window) with at least 20% left: use it now,
   it is wasted after the reset.
2. Light tasks: a local Ollama model, which costs no quota.
3. The subscription with the most room that won't run out early at the current pace.
4. One that will run out early.
5. An installed subscription CLI whose limit usage is unknown, as a fallback. Unknown usage is reported
   explicitly and never treated as 100% remaining.
6. Heavy tasks fall back to a local model last. A used-up limit is never picked.

It only reads the ledger (no network, no SSH), so it is fast enough for `$(...)`. The home screen's advice
also says when a limit is about to reset with plenty left, and agents can ask the same question through the
MCP tool `pick`.

## Limit guard (Claude Code and Codex hooks)

Optional hooks so the agent itself knows when a limit or the budget is running low. `computai --setup`
asks whether to install them and shows the `settings.json` diff first.

- **PreToolUse** (only when launching subagents, `Task|Agent`) and **Stop**: when a limit has less than
  `[guard] warn_left` percent left (default 10), or this month's forecast is over `[budget] monthly_usd`, the
  agent gets a reminder ("prefer fewer, smaller subagents") and you see it as a message.
- `[guard] strict = yes`: new subagents are refused while that is the case, and the agent is told why.
- They never answer "allow", so your own permission settings still apply. Any error (no ledger, old or
  broken state) lets everything through silently.
- Fast: every sync writes a small guard state to the ledger, and the hook is a generated script
  (`claude-hook.py` in the data folder) that only reads that row, in about 20 ms. No network, no prompts read.
  `computai --hook claude-pretool|claude-stop` gives the same answer, more slowly.
- Codex uses the same hooks (`~/.codex/hooks.json`, subagents are `spawn_agent`). Codex runs a new hook only
  after you trust it once: open `codex` and type `/hooks`.

## MCP server (for agents)

`computai --mcp` speaks the Model Context Protocol on stdin/stdout, so an agent can check its own
budget before starting something expensive. Tools: `usage_summary` (a month's cost per source and
model), `limits`, `budget` (month-end forecast and today), `machines` (GPU use, loaded models, what
still fits), `advice` and `pick` (which agent should take this subtask; see below). All read-only. Register it with your agent as a stdio server whose command is
`computai --mcp` (for Claude Code, something like `claude mcp add computai -- computai --mcp`; for
Codex, an `[mcp_servers.computai]` entry with `command = "computai"` and `args = ["--mcp"]`).

## How the numbers are worked out

- **API-equivalent cost** = tokens × the prices in `prices.ini`, computed when you ask, so
  changing a price changes past months too. Cloud rows carry their own cost.
- **Energy** integrates power between consecutive samples (average of the two × time). Gaps over
  10 minutes are not integrated, so `hours` in the machine table shows how much was covered.
  Power is measured GPU power + `base_watts` when GPU power is readable, otherwise interpolated
  between `idle_watts` and `max_watts` by load.
- **AI share** is the share of sampled time in which the machine was doing inference: token
  counters moved, requests were running, the proxy saw traffic, Ollama's `expires_at` moved, or
  (non-Apple GPUs) a model was loaded and the GPU was over 20 % busy. Mac GPU use includes drawing
  the screen, so it is not used as a signal.
- **J/token** = energy during AI time ÷ generated tokens.

## Troubleshooting

- *A model shows "?" cost*: add it to `prices.ini`.
- *No Claude percentage*: make sure the `claude` CLI is installed and logged in (Pro/Max only), then try `computai --claude-limits`.
- *A machine never appears*: `--sample`, `--live` and `--web` show why ("cannot read: ..."). Run
  `ssh -o BatchMode=yes HOST true`; it must work without prompts. "Host key verification failed" means
  known_hosts has the key under another name: use the name or IP you normally ssh to (for Tailscale
  machines often the 100.x address), or run `ssh HOST` once by hand.
- *"ignoring secrets.ini"*: `chmod 600 ~/.config/computai/secrets.ini`.
- *Tailscale is online but SSH times out*: if the error says `Tailscale SSH requires an additional check`,
  run `ssh USER@HOST` in a terminal and open the authentication link it prints. Tailscale's
  [SSH check mode](https://tailscale.com/docs/features/tailscale-ssh) can require this again when its
  check period expires; `BatchMode=yes` cannot complete browser authentication. ComputAI keeps retrying
  after you authenticate. A failed node counts once in the dashboard, and old samples do not count online.
- *Reporting a bug*: paste `computai --doctor --redact`. It replaces machine names, SSH hosts, IPs, project
  names, paths under your home folder, emails and your user name with codes (`machine-1`, `ip-1`, `~/path-1`).
- *New version*: `computai --doctor` and the end of interactive commands say when one is out (checked at
  most once a day; `[general] update_check = no` turns it off). Update by running the installer again.
- *Start over*: delete `ledger.sqlite`; logs are re-imported on the next run.
- *Uninstall*: delete the `computai` file, `~/.config/computai` and `~/.local/share/computai`.


## Token breakdown and local request tracing (beta.3)

```sh
computai --tokens
computai --tokens --month 2026-10 --json
computai --proxy --tag test
# Point your test client at 127.0.0.1:11435, then use another terminal:
computai --local-requests
computai --local-requests 50 --machine m1m --model qwen3:8b --tag test --json
```

`--tokens` defaults to the last 30 calendar days including today, matching the default card; explicit
month/since/until filters select another range. Exact counts and percentages separate uncached input,
cache reads, 5m/1h cache writes and output. Reasoning is already in output and is shown as a subset.
B = billion, M = million; repeated cache reads count again, so totals are not unique text. Cache share
uses all tokens while input cache-hit rate excludes output. Cloud GPU rows are excluded. Top five
sources, models and projects are local reports; published cards still omit project and machine names.
Web usage has an expandable breakdown; the TUI spend tab links to the CLI; SVG cards explain cache
share and output, with accessible full counts.

`--local-requests [N]` defaults to today's latest 20 requests, max 200, with date/machine/model filters.
`--tag` labels new proxy requests or filters this query: test, production, benchmark; unset means no label.
Timestamps mark forwarding start. Elapsed time runs from starting upstream forwarding to completing
transfer, including connection, queue, input processing and generation. Output tok/s = output / elapsed;
it is **not generation-only speed or time to first token**. Failed/unknown usage is `?`, never fabricated zero.
Outcomes describe HTTP/transfer success, HTTP error, upstream failure, client disconnect or missing usage;
they do not inspect whether the generated content fulfilled a task.

Only new POST requests to /api/chat, /api/generate, /v1/chat/completions, /v1/completions and /v1/responses
are traced. No query strings, headers, prompts, responses or error bodies are stored. Metadata is separate
from token usage; automatic counter sampling may suppress usage rows while retaining request metadata,
without adding tokens twice. Explicit `--no-ledger` disables both persistent usage and request metadata,
leaving in-memory /metrics. Existing --local-history remains available; old rows cannot recover timings,
outcomes or labels. The TUI local tab prioritizes requests when available; web shows both histories.
Restart existing proxy/TUI/web processes to load the new code. These features are available since beta.3.
