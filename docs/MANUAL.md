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
  count too), every 10 minutes:
  - Claude: ask the official `claude` CLI (`claude -p /usage`, a local command that calls no model and uses
    no quota); Pro and Max accounts only. Setting Claude Code's status line to `computai --statusline`
    (see [one-line.md](one-line.md)) also works and updates on every reply.
  - Codex: ask the official `codex` CLI (`codex app-server`); the limit windows in its logs are read too.
  - The official CLIs handle their own login; ComputAI only receives percentages and reset times.
    `[claude]` / `[codex] poll_minutes = 0` turns it off.

## Commands

All commands accept `--json`. Ranges: `--month [YYYY-MM]`, `--since YYYY-MM-DD`,
`--until YYYY-MM-DD` (inclusive); the default is this month.

| Command | What it does |
|---|---|
| `computai` | On a terminal: the live dashboard. Otherwise the same as `--summary`. |
| `--summary [--by model\|project\|session\|day]` | Totals per source and model, API-equivalent cost, plan comparison, limits, machines, cloud and alerts. |
| `--sync` | Import new usage and print how many rows were added per source. |
| `--line [--sep " · "]` | One line: each subscription's fullest limit window and today's cost. Re-reads logs at most every 30 s. |
| `--statusline` | For Claude Code's `statusLine`: records Claude's limits from stdin, prints `--line`. |
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

- `computai` / `--live` (cyber theme) has tabs: **1 overview** (fits one screen: limit gauges, one line per machine, spend, the top alerts and advice), **2 limits**, **3 machines**, **4 local models**, **5 spend**; `1`-`5` or `Tab` switch, `q` quits. Limits show what is left by default (`[general] limits = used` flips it). The panels, top to bottom:
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
- `--web`: open `http://127.0.0.1:8765/`. To see it on a phone, keep it on loopback and use an
  SSH tunnel (`ssh -L 8765:127.0.0.1:8765 host`) or `tailscale serve 8765`. `--web 0.0.0.0:8765`
  exposes your usage, project names and machines to the network and prints a warning.
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

- If the machine is already in `[machines]`, the proxy only keeps totals, so nothing is counted twice.
- On a machine that another computai samples, use `--no-ledger`.

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
- `handle` sets the title; it defaults to the repo's GitHub account.
- `lang` sets the card's language.
- `--setup` asks for all of this and finds the profile repo on disk. Before pushing it rebases onto any commit a bot pushed in the meantime.

## Local model benchmark

`computai --bench [--machine NAME]` sends the same fixed prompt to every running inference server for a
few seconds. It measures tokens per second, samples the machine's power while it generates, and works
out joules per token and the electricity per million tokens. It compares that with the cheapest output
price in `prices.ini`; hardware is not counted. Only usage fields are read from the answers.

Macs need `idle_watts` / `max_watts` (or a smart plug) for the power columns.

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

## MCP server (for agents)

`computai --mcp` speaks the Model Context Protocol on stdin/stdout, so an agent can check its own
budget before starting something expensive. Tools: `usage_summary` (a month's cost per source and
model), `limits`, `budget` (month-end forecast and today), `machines` (GPU use, loaded models, what
still fits) and `advice`. All read-only. Register it with your agent as a stdio server whose command is
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
- *Start over*: delete `ledger.sqlite`; logs are re-imported on the next run.
- *Uninstall*: delete the `computai` file, `~/.config/computai` and `~/.local/share/computai`.
