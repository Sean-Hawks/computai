# ComputAI

**Friends beta:** [v0.1.0-beta.1](https://github.com/Sean-Hawks/computai/releases/tag/v0.1.0-beta.1) · [installation, limits and feedback](docs/RELEASE-v0.1.0-beta.md). The downloaded installer pins this tested version.

**Where your compute and AI money goes.** One ledger for your Claude and ChatGPT
subscriptions, the local models on your homelab, the machines they run on and the cloud
GPUs you rent: tokens, GPU hours, kWh and money, side by side.

[繁體中文說明](README.zh-TW.md) · [Manual](docs/MANUAL.md) · [使用手冊](docs/MANUAL.zh-TW.md) · [Where ComputAI shows up](docs/SURFACES.md)

> **Want to share your AI usage on Threads or in a README?**
> beta.2 development: `computai --create` → choose a period/layout → download PNG or SVG. No GitHub setup needed.
> From this development checkout, `sh install.sh --create` installs and opens the creator in one step. Released beta.1 does not include it yet. [First-card guide (繁中)](docs/MAKE-A-CARD.zh-TW.md).

[Pick a card style](#choose-your-card-style) · [Make your first card](#make-your-first-card) · [Daily GitHub updates](#your-ai-ops-card-for-your-github-profile)

## Choose your card style

Turn your AI usage into a card for Threads, a monthly recap or your GitHub README.
Start with the Web/TUI look, or choose one of ten profile styles below. All previews use demo data.

| Web/TUI sharing card | Profile cards: minimal, paper, github, terminal |
|---|---|
| <img src="docs/images/share-preview.png" width="270" alt="Web/TUI sharing card: white usage totals and a daily activity chart on black"> | <img src="docs/images/card-styles-preview.png" width="660" alt="Four profile styles: minimal monochrome banner, paper portrait, GitHub dashboard and terminal banner"> |
| Black and white, clear totals and activity trends. Square, portrait, wide or README formats; download PNG or SVG with `--create`. | Quiet banners, a warm paper summary or an activity dashboard. Export SVG with `--card`. |

Prefer neon? These six styles use a HUD with cut corners, activity grids and decorative animation:

| `netrunner` · cyan / pink / yellow | `arasaka` · red / black |
|---|---|
| ![Netrunner profile card](docs/images/card-netrunner.svg) | ![Arasaka profile card](docs/images/card-arasaka.svg) |
| **`militech` · yellow / orange** | **`amber` · violet / gold** |
| ![Militech profile card](docs/images/card-militech.svg) | ![Amber profile card](docs/images/card-amber.svg) |
| **`matrix` · terminal green** | **`synthwave` · magenta / cyan** |
| ![Matrix profile card](docs/images/card-matrix.svg) | ![Synthwave profile card](docs/images/card-synthwave.svg) |

### Pick the look that fits your page

| Profile style (`--card-style`) | Look and use | Default layout | Available in |
|---|---|---|---|
| `minimal` | Monochrome, whitespace; a compact README banner | `compact` | beta.2 development |
| `paper` | Warm paper and serif type; a vertical summary | `portrait` | beta.2 development |
| `github` | Statistic panels, activity grid and model shares | `dashboard` | beta.2 development |
| `terminal` | Monospace console with a straight frame | `compact` | beta.2 development |
| `netrunner` | Cyan, pink and yellow; the default cyberpunk HUD | `hud` | beta.1 |
| `arasaka` | Red accents; a stark red and black HUD | `hud` | beta.1 |
| `militech` | Yellow and orange; a high-contrast HUD | `hud` | beta.1 |
| `amber` | Violet and gold; a warmer neon palette | `hud` | beta.1 |
| `matrix` | Green; a terminal-inspired HUD | `hud` | beta.1 |
| `synthwave` | Magenta and cyan; retro neon | `hud` | beta.1 |

Every profile style has dark and light versions, with English or Traditional Chinese labels.
The Web/TUI sharing card, four new styles, layout overrides and local gallery need this beta.2 development checkout;
the released beta.1 has the six neon styles. The creator uses the Web/TUI look; choose profile styles through `--card`.

### Make your first card

With Python 3.8+ in this development folder, open the creator without installing:

```sh
python3 ./computai --create                 # Windows: py -3 computai --create
```

Choose social or GitHub README, a period and a layout, then download PNG or SVG.
No GitHub setup is needed. [First-card guide (繁中)](docs/MAKE-A-CARD.zh-TW.md).

For the profile styles, run these from the same folder, then open `styles.html` or `card.svg`:

```sh
python3 ./computai --card --html styles.html   # compare all ten styles, dark/light and layouts
python3 ./computai --card --card-style minimal --svg card.svg
python3 ./computai --card --card-style paper --card-theme light --svg card.svg
python3 ./computai --card --card-style amber --svg card.svg
```

Add a downloaded SVG to your README:

```markdown
![My AI usage](card.svg)
```

These commands write local files. Share the downloaded image; the creator HTML contains your selectable history.
Once installed, use `computai` in place of `python3 ./computai`.

### Adjust the layout and save your favourite

Style chooses colours and fonts; `--card-layout` chooses dimensions and content:
`auto` follows the style, `hud` is 900×390, `compact` 720×230, `dashboard` 900×360 and `portrait` 420×610.
Compact banners show tokens, API equivalent, active days, usage mix and top model;
dashboard and portrait also show activity grids and hours. The four new styles are static in their default layouts.

```sh
computai --card --card-style github --card-layout compact --svg card.svg
computai --set card.style=paper --set card.layout=portrait  # daily updates use these too
computai --set 'card.colors=#ff6b6b, #ffd93d'               # custom accent pair
computai --set card.handle=NEO                             # display name
computai --set card.lang=zh                                # en or zh
computai --set card.credit=no                              # hide the small credit
```

CLI options override saved `[card]` settings. For both light/dark SVGs and daily updates,
follow the [GitHub profile setup](#your-ai-ops-card-for-your-github-profile).

## See your usage live

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

## Features to try in local beta.2 development

`computai --tokens` explains cache and output totals, also clarified on shareable cards.
`computai --statusline` adds Claude's model, context and last request; `--statusline-view compact` keeps one line.
`computai --proxy --tag test` records new request durations and HTTP outcomes; inspect them with `computai --local-requests`.
Only requests through the updated proxy have this detail; no prompts or responses are stored.
These are unreleased local development features; [usage and counting rules](docs/MANUAL.md#token-breakdown-and-local-request-tracing-beta2-development).

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
computai --profile --html profile.html --who hawks  # beta.2: profile with monthly and annual reports
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

## Personal history profile and reports (beta.2 development)

`computai --profile --html profile.html` writes a local page with selectable monthly and annual reports:
exact token buckets, daily activity, top models, source shares and active days. Switch light/dark themes or print.
Use `--profile 2026-09` or `--profile 2026` to choose the initial report, `--who NAME` for a display name,
and `--json` for aggregate data. `--lang zh` renders Traditional Chinese.

GUI users can use existing backend usage logs; no Claude Code status line is needed. Record sources do not
identify T3 or Codex GUI, and unavailable history cannot be recovered. Source coverage and partial periods
are explicit. B means billion, including repeated cache reads; reasoning is already within output.
API-equivalent values use current configured rates for priced models and are not bills.

Only dates, usage, sources and models enter the page: no conversation contents, project paths, machine
addresses or sessions. It imports local logs only, with no API, SSH or model calls; `--no-sync` uses the ledger
alone. The single HTML includes all observed periods and stays local; nothing is published automatically.
The published beta.1 does not include this feature.

Use `computai --create` for a preview, period/layout selection and PNG/SVG downloads, including a README banner.
The default follows the calm Web/TUI design. For scripted single-image exports:

```sh
computai --profile --share-layout square --html share.html --svg share.svg
computai --profile 2026-09 --share-layout portrait --html month-share.html
computai --profile 2026 --share-layout wide --svg year-share.svg
```

Sizes are square 1080×1080, portrait 1080×1350 and wide 1200×630. The share page can download an original-size
PNG locally in your browser, or the SVG. Images show dates, cache share, output and activity days; portrait
also shows usage trends. Share HTML/SVG contain only the selected period, with no billing or ability claims.
`--svg` also enables this mode; a simultaneous HTML export becomes a single-card preview. Plain HTML remains
the full history page. Explicit `--card-style amber` or another existing style selects a legacy HUD without changing saved settings.
The creator HTML is a private tool containing aggregates for selectable periods; share its downloaded PNG/SVG files.

## Your AI ops card for your GitHub profile

A card for your profile README (`github.com/<you>/<you>`) that shows how AI agents work for you: how many tokens, for how many hours, how many at once, with which models. It is rendered on your own machine from your own usage logs, and can be updated once a day. [Choose your style above](#choose-your-card-style), then use this setup to add it to your profile and keep it fresh.

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
