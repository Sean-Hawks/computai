# ComputAI

**Friends beta:** [v0.1.0-beta.1](https://github.com/Sean-Hawks/computai/releases/tag/v0.1.0-beta.1) · [installation, limits and feedback](docs/RELEASE-v0.1.0-beta.md). The downloaded installer pins this tested version.

**Where your compute and AI money goes.** One ledger for your Claude and ChatGPT
subscriptions, the local models on your homelab, the machines they run on and the cloud
GPUs you rent: tokens, GPU hours, kWh and money, side by side.

[繁體中文說明](README.zh-TW.md) · [Manual](docs/MANUAL.md) · [使用手冊](docs/MANUAL.zh-TW.md) · [Where ComputAI shows up](docs/SURFACES.md)

> **Just want the AI ops card for your GitHub profile?**
> `curl -fsSL https://raw.githubusercontent.com/Sean-Hawks/computai/main/install.sh | sh && computai --card --setup` · [what it shows](#your-ai-ops-card-for-your-github-profile)

```
$ computai --summary --month 2026-09
ComputAI  2026-09  (2026-09-01 - 2026-09-30)

                           requests    input  cache rd  cache wr   output  API equiv
claude
  claude-opus-5                 924     1.9k      123M      3.5M     718k    $115.39
  claude-opus-5-5               533     1.1k      174M      4.5M     633k     $82.45
  ...
  plan: Claude Max 5x, $100.00 for this range -> usage worth 2.9x the fee
codex
  gpt-6-astra                  4.9k    25.4M      541M         0     2.9M    $938.96
  ...
```

![Live terminal dashboard: start-up check, then the HUD](docs/images/live.svg)

`computai --web` gives the same view in a browser (phone layout included); `computai --tailscale` opens it on your
own tailnet over HTTPS while the server stays on 127.0.0.1:

![Web dashboard](docs/images/web.png)

*(Screenshots use demo data. The default `cyber` theme follows [docs/DESIGN.md](docs/DESIGN.md): the top line says whether anything needs you, colours only mean something. Prefer the slurmtop look? `--theme classic` or `computai --set general.theme=classic`.)*

## What it does

| | Source | What you get |
|---|---|---|
| **Subscriptions** | Claude Code and Codex session logs on this computer | tokens per model, cache and reasoning shown separately, cost at API prices versus your monthly fee, per-project breakdown, Codex and Claude limit windows with reset countdowns |
| **More agents** | Gemini CLI chat recordings, OpenCode's database, Cursor's usage CSV export | tokens per model and project, cost at API prices, subagents |
| **API** | Anthropic and OpenAI admin usage APIs (optional) | organisation usage per model and day |
| **Local models** | Ollama, llama.cpp, vLLM, SGLang, LM Studio, OpenAI-compatible servers | which models are loaded, tokens (from `/metrics`, or from the optional `--proxy` for Ollama), "model loaded but idle" alerts |
| **Machines** | SSH + `sh` (nothing to install), or this computer | CPU, GPU, power, kWh, electricity cost, AI share of the time, joules per token |
| **Cloud GPUs** | RunPod, Vast.ai, Lambda (read-only API calls) | what is running, what it costs per hour, and **GPUs that sit idle while still billing** |

On top of the ledger: cache-efficiency analysis (which sessions keep re-writing the prompt
cache and what that cost), a month-end forecast with an optional budget, a plan simulator,
a GPU payback calculator and time-of-use electricity prices (Taipower two-tier presets).

Not sure whether to hand a task to Claude, Codex or a local model? `$(computai --pick) "tidy up this PR"` uses
whichever limit is about to reset unused, avoids one that will run out early, and sends light tasks to a local model.

Using Claude or Codex on more than one computer? Point them at a shared folder (`[devices] folder`) or pull
over SSH and the ledger counts all of them, usage numbers only ([how](docs/MULTI-DEVICE.md)).

Also: `--discover` finds machines in `~/.ssh/config` and Tailscale; each machine shows how large a model
still fits; smart plugs (Shelly, Tasmota, Home Assistant) give measured power; `--wake` sends Wake-on-LAN;
`--mcp` lets agents ask about their own budget; `--weekly --send` posts a weekly summary to Discord or
Telegram; `--wrapped` makes a Spotify-Wrapped-style story page and share card, `--card` a GitHub profile card (`--recap` is the older year card); `--csv` exports records; `--totals`/`--lab` combine a
group's totals; `--lang zh` switches the dashboards to Traditional Chinese.

## Install

Python 3.8 or newer, standard library only. macOS, Linux and Windows.

```sh
sh install.sh                 # macOS / Linux: installs to ~/.local/bin/computai
```

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1    # Windows
```

Or just copy the single `computai` file anywhere on your `PATH`.

## Make it yours (two minutes)

```sh
computai --setup      # step by step: your plans, Claude limits, machines, power, electricity, keys
computai --doctor     # what is detected, what is missing, and the exact command to fix each gap
computai              # the dashboard
```

Claude Code and Codex usage needs no setup at all. `--setup` asks one thing at a time, shows the
current or suggested value (Enter accepts it, `s` skips), detects your plan from the logs where it can,
finds machines in `~/.ssh/config` and Tailscale, suggests power settings from the hardware it sees
(laptop or desktop, Apple tier, measured GPU power), and only writes after you confirm, keeping a backup.

Everything stays editable by hand in `~/.config/computai/config.ini`, or from scripts:

```sh
computai --set 'plans.claude=Claude Max 5x, 100, 2026-10-03' --set machine.wsl.base_watts=60
computai --unset plans.codex
computai --discover --add             # add every reachable machine with suggested power
```

## Use

```sh
computai                          # live dashboard: tabs 1-5 (overview, limits, machines, local models, spend), q quits
computai --summary --month        # this month; --since 2026-09-01, --by project|day|session
computai --line                   # Claude 42%｜Codex 100% (1d0h)｜today $6.9
computai --analyze                # forecast, plan check, cache waste, energy
computai --web                    # http://127.0.0.1:8765/ (phone layout) and /metrics
computai --report --month 2026-09 --html september.html
computai --sample                 # read every machine in [machines] once
computai --cloud                  # RunPod / Vast.ai / Lambda
computai --proxy                  # count Ollama tokens on 127.0.0.1:11435 -> :11434
computai --payback 1800 --gpu-watts 450
computai --discover               # which of my machines can ComputAI read?
computai --bench                  # tokens/s and electricity per 1M tokens for each local model
computai --install-watch          # notify me when a limit runs low, runs out or resets (at login)
computai --once --lang zh         # 中文、印一次
computai --wrapped 2026-09        # Spotify-Wrapped-style recap of a month (or 2026 for a year)
computai --wrapped --html story.html --svg card.svg   # story page + 1200x630 share card
computai --card --svg card.svg    # small card for your GitHub profile README (--card-theme light)
computai --card --publish ~/code/me/assets   # commit the card into your profile repo (no push without --push)
```

Every command takes `--json`. The first run writes `config.ini` and `prices.ini` to
`~/.config/computai/` (see `computai --paths`); edit them to set your plans, machines,
electricity price and API prices. Every price carries the date it was checked.

Status bars: `computai --line` for tmux and SwiftBar, `computai --statusline` as Claude Code's
status line. See [docs/one-line.md](docs/one-line.md). Claude's limit percentages come from the
`claude` CLI on their own (no status line needed), so T3 Code and other machines count too.

## Your AI ops card for your GitHub profile

A cyberpunk card for your profile README (`github.com/<you>/<you>`) that shows how AI agents work for you: how many tokens, for how many hours, how many at once, with which models. It is rendered on your own machine from your own Claude Code and Codex logs, and updated once a day. There is no web service and no upload.

![ComputAI profile card](docs/images/card-netrunner.svg)

### Quick start

```sh
curl -fsSL https://raw.githubusercontent.com/Sean-Hawks/computai/main/install.sh | sh
computai --card --setup
```

`--card --setup` asks a few questions and does the rest:

1. It finds your profile repo on disk. If it isn't cloned, it offers to clone it with `gh`. If it doesn't exist on GitHub yet, it offers to create it, and only does so when you say yes.
2. You pick a style.
3. It writes the first card and commits it.
4. It adds the card to your README.
5. It pushes, if you want.
6. It offers to keep the card fresh every day in the background (`computai --install-watch`).

Claude Code and Codex need no setup. If you have used them on this computer, the card already has data.

### What the card shows

| Part | What it means |
|---|---|
| **Tokens** | Every token that went through your agents in the last 30 days (input, cache, output). |
| **At API prices / plan value** | What those tokens would cost at API list prices (`prices.ini`), and how many times over your subscriptions paid for themselves. |
| **Agent hours** | Time your agents were actually working: gaps under 5 minutes inside a session count, longer pauses don't. |
| **Peak parallel** | The most agent sessions working at the same moment. |
| **Longest run** | The longest stretch one session worked without a 5-minute pause. |
| **Cache hit** | Share of input served from the prompt cache. Higher means cheaper, faster agents. |
| **Activity // 13W** | One square per day for 13 weeks; the brightest squares are your busiest days. |
| **Fleet** | Split between Claude Code, Codex and local models. |
| **Rank** | A level from all-time tokens (the square root of millions, so it gets harder), with a title: INITIATE, PROMPT RUNNER, CONTEXT HACKER, CACHE WEAVER, TOKEN ALCHEMIST, NETRUNNER, GHOST IN THE SHELL, AI OVERLORD. |
| **Prompts / subagents** | Requests sent, and sessions where agents spawned subagents. |
| **Loadout** | Your top three models and their share. |
| **Facts** | Work rhythm (night owl, early bird, nine to five, evening hacker), peak hour, current streak, money the cache saved. |
| **Badges** | 100M / 1B / 10B CLUB (all-time tokens), STREAK xN (7+ days in a row), your rhythm, CACHE LORD ($1,000+ saved by the cache), HOMELAB (local models used), POLYGLOT (3+ models with 5%+ share), MAXED OUT (a limit hit 100%). |
| **Pulse** | The line under the stats is your daily usage over 30 days. |

### Styles

Beta.2 development adds four styles with different default layouts; the published beta.1 does not include them.

| Style | Appearance and default layout |
|---|---|
| `minimal` | Quiet monochrome banner (`compact`) |
| `paper` | Warm paper, serif typography, vertical summary (`portrait`) |
| `github` | Statistic panels, activity grid and model shares (`dashboard`) |
| `terminal` | Plain monospace console, square frame (`compact`) |

![Four new card styles using demo data](docs/images/card-styles-preview.png)

```sh
computai --card --html styles.html                     # compare all ten styles, light/dark and layouts locally
computai --card --card-style minimal --svg card.svg
computai --card --card-style paper --card-theme light --svg card.svg
computai --card --card-style github --card-layout compact --svg card.svg
computai --set card.style=paper --set card.layout=portrait  # also used by daily updates
```

`--card-layout` accepts `auto` (follow the style), `hud` (900×390), `compact` (720×230),
`dashboard` (900×360) or `portrait` (420×610). Style selects colours and fonts; layout selects dimensions and content.
CLI options override `[card]` settings. Compact banners show tokens, API equivalent, active days, usage mix and top model;
the dashboard and portrait also show activity grids and hours. New styles are static by default.
The original six styles retain their HUD layout and decorative animation:

| `arasaka` | `militech` |
|---|---|
| ![arasaka](docs/images/card-arasaka.svg) | ![militech](docs/images/card-militech.svg) |
| `synthwave` | `matrix` |
| ![synthwave](docs/images/card-synthwave.svg) | ![matrix](docs/images/card-matrix.svg) |
| `amber` | light mode |
| ![amber](docs/images/card-amber.svg) | ![netrunner light](docs/images/card-netrunner-light.svg) |

```sh
computai --set card.style=arasaka                 # netrunner (default), arasaka, militech, amber, matrix, synthwave
computai --set 'card.colors=#ff6b6b, #ffd93d'     # your own accent pair
computai --set card.handle=NEO                    # the name after SYS. (default: your GitHub account)
computai --set card.lang=zh                       # card language (en, zh)
computai --set card.credit=no                     # drop the small GEN BY COMPUTAI
```

Every style has a light version (`computai-card-light.svg`). The README snippet shows it to visitors who use light mode.

### Keeping it fresh, by hand or in scripts

Once a day `computai`, `computai --web` or the background watcher rewrites both SVGs and commits them. If `push = yes`, it also rebases onto anything a bot pushed meanwhile and pushes. The settings live in `config.ini`:

```ini
[card]
repo = ~/Documents/you/assets   ; folder inside your profile repo
period = 30d                    ; 30d, month, year or all
push = yes
style = netrunner
```

```sh
computai --card --svg card.svg                       # just write a card (--card-theme light, --period year)
computai --card --publish ~/Documents/you/assets     # write both cards and commit them (no push)
computai --card --publish ~/Documents/you/assets --push
```

The snippet `--card --setup` adds to your README:

```html
<a href="https://github.com/Sean-Hawks/computai">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="assets/computai-card-light.svg" />
    <img src="assets/computai-card.svg" alt="AI ops: tokens, agent hours, parallel agents, activity, rank and models" width="100%" />
  </picture>
</a>
```

### What is on the card, and what is not

- **On the card**: totals, model names, your GitHub handle, the time of the last update.
- **Never on the card**: project names, folder paths, session ids, machine names, prompts or responses.
- **What runs**: only `git` against your own profile repo. Nothing is sent anywhere else.
- **The SVG itself**: no scripts or external resources. Its animations (glitch, scan, cursor) are decoration only. The card is complete without them, and they stop for visitors who prefer reduced motion.

### Troubleshooting

- **The card says NO SIGNAL**: no Claude Code or Codex usage was found on this computer. `computai --doctor` shows where it looked.
- **The card stopped updating**: run `computai --install-watch` again. On macOS the log is `~/.local/share/computai/watch.log`.
- **The push fails**: git needs to be able to push to your profile repo (`gh auth login`, or an SSH key). Fix that, then run `computai --card --publish <folder> --push` once.
- **The font looks different on GitHub**: the card asks for JetBrains Mono and falls back to the visitor's monospace font.

## Privacy and security

- Claude limits for your whole account come from asking the official `claude` CLI (`claude -p /usage`, a local command that calls no model): every 10 minutes when calm, down to every minute while a limit burns fast, and 30 seconds after a reset. The CLI uses its own login; ComputAI only receives percentages and reset times and ignores the rest of the report (`[claude] poll_minutes = 0` turns it off).
- Codex limits for your whole account (every machine and person on it) come from asking the official `codex` CLI (`codex app-server`, `account/rateLimits/read`), on the same burn-rate schedule. The CLI uses its own login; ComputAI only receives percentages and reset times (`[codex] poll_minutes = 0` turns it off).
- Reads only usage fields from your logs. Prompts and responses are never read into the
  ledger, stored or sent anywhere. `~/.codex/auth.json` and Claude's OAuth tokens are never read.
- API keys come from environment variables or a `chmod 600` `secrets.ini`, and never appear in
  logs, `--json`, `/metrics` or error messages.
- `--web` and `--proxy` listen on `127.0.0.1` unless you say otherwise; the web server rejects
  requests for other host names (DNS rebinding).
- Cloud and admin APIs are only ever called with read-only "list" requests.
- Once a day, interactive commands read the first 2 KB of `computai` on GitHub to see if a newer version is out.
  Nothing about you or your usage is sent; `[general] update_check = no` (or `COMPUTAI_NO_UPDATE_CHECK=1`) turns it off.

## Tests

```sh
tests/run.sh                    # unit tests on python3 and, if present, Python 3.8
python3 tests/e2e_ollama.py     # end-to-end: real Ollama behind the proxy (needs ollama + qwen3:0.6b)
```

## Credits

Machine sampling, GPU detection, the web server's security headers and the Prometheus
output are ported from [slurmtop](https://github.com/Sean-Hawks/slurmtop) (MIT, same author,
commit 84cd35d). MIT licence.
