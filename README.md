# ComputAI

**Where your compute and AI money goes.** A terminal dashboard and browser GUI for AI usage,
subscription limits, local inference and compute costs. Track Claude, Codex, your homelab and
cloud GPUs in one ledger: tokens, GPU hours, kWh and money.

Single Python file · Standard library only · Python 3.8+ · macOS, Linux and Windows

[繁體中文](README.zh-TW.md) · [Quick start](#quick-start) · [Manual](docs/MANUAL.md) · [Release notes](docs/RELEASE-v0.1.0-beta.md)

**Current release:** [v0.1.0-beta.1](https://github.com/Sean-Hawks/computai/releases/tag/v0.1.0-beta.1).
Features marked **beta.2 development** are available in this development checkout.
You can also export [usage cards for social posts and GitHub READMEs](#cards-and-sharing).

## Dashboards

### Terminal UI

Run `computai` for a live overview of limits, machines, spending and alerts.
Use `1`–`6` or `Tab` to switch between overview, limits, machines, local models, spend and timeline; `q` quits.

![ComputAI terminal dashboard](docs/images/live.svg)

### Browser GUI

Run `computai --web`, then open `http://127.0.0.1:8765/`.
The browser shows the same ledger with usage charts, machine status and alerts, including a mobile layout.

![ComputAI browser dashboard](docs/images/web.png)

Both screenshots use demo data. Use `--lang zh` for Traditional Chinese and `--theme classic` for the alternative dashboard theme.
With Tailscale installed and signed in, `computai --tailscale` makes the browser GUI available over HTTPS on your own tailnet;
the local server continues to listen on `127.0.0.1`.

## Quick start

### Install

macOS / Linux — install the released beta to `~/.local/bin/computai`:

```sh
curl -fsSL https://raw.githubusercontent.com/Sean-Hawks/computai/v0.1.0-beta.1/install.sh | sh
```

Windows — download and extract the ZIP from the [release page](https://github.com/Sean-Hawks/computai/releases/tag/v0.1.0-beta.1), then run in that folder:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

Ensure the install directory is on `PATH`; on Windows, reopen your terminal after installation.
To use this development checkout, run `sh install.sh` on macOS/Linux or the PowerShell command above on Windows.
You can also run the single file directly with `python3 ./computai` (Windows: `py -3 computai`).

### Launch

```sh
computai                 # terminal dashboard
computai --web           # browser GUI at http://127.0.0.1:8765/
```

Run either command in its own terminal. Claude Code and Codex usage is detected from supported local logs.
The first run may ask you to confirm your subscription plans. Stop the browser server with `Ctrl-C`.

```sh
computai --setup         # configure plans, machines, electricity and optional API keys
computai --doctor        # inspect detected sources and missing configuration
```

Remote machines, cloud providers and API usage are optional. Set up the sources you use.

## What it tracks

| Source | Data | What you can see |
|---|---|---|
| **Claude Code / Codex** | Local session usage logs; official CLI quota queries | Tokens per model and project, cache and reasoning, subscription limits and reset countdowns |
| **Gemini CLI / OpenCode / Cursor** | Local recordings, usage database or exported CSV | Tokens, model shares, project breakdowns and API-equivalent cost |
| **Local models** | Ollama, llama.cpp, vLLM, SGLang, LM Studio and compatible servers | Loaded models, recorded tokens, inference speed and idle-model alerts |
| **Machines** | This computer or SSH + POSIX `sh` | CPU, GPU, power, kWh and electricity cost; no remote agent required |
| **Cloud GPUs** | RunPod, Vast.ai and Lambda read-only APIs | Running instances, hourly costs and idle resources that are still billing |
| **API organisations** | Optional Anthropic and OpenAI admin APIs | Usage per model and day |

Cost analysis includes cache efficiency, month-end forecasts, budgets, subscription comparisons,
GPU payback and time-of-use electricity pricing. API-equivalent values use your configured rates and are estimates, not bills.
Local token coverage depends on service metrics or traffic through the optional token-counting proxy.

## Common commands

| Task | Command |
|---|---|
| Monthly usage | `computai --summary --month` |
| Usage by project | `computai --summary --month --by project` |
| Agent activity timeline | `computai --timeline` |
| Forecast and cost analysis | `computai --analyze` |
| Save an HTML report | `computai --report --month 2026-09 --html september.html` |
| Discover machines | `computai --discover` |
| Count local inference tokens | `computai --proxy` |
| Benchmark local models | `computai --bench` |
| Limit notifications at login | `computai --install-watch` |
| Status bars | `computai --line` |

Use `computai --help` for all options and the [manual](docs/MANUAL.md) for source setup and counting rules.
The browser also exposes `/metrics` for Prometheus.

For usage across computers, see [multi-device setup](docs/MULTI-DEVICE.md).
For tmux, SwiftBar and Claude Code, see [status line integration](docs/one-line.md).
Agent routing (`--pick`), MCP (`--mcp`), weekly summaries and team totals are covered in the manual.

## Configuration

The first run creates `config.ini` and `prices.ini`. Run `computai --paths` to locate your settings and SQLite ledger.
On macOS/Linux, settings default to `~/.config/computai/`; Windows uses the application data directories.
Plans, API prices and electricity tariffs stay editable, with dates for checked prices.

```sh
computai --set general.lang=zh
computai --set general.theme=classic
```

Use `--setup` for guided configuration or `--set` / `--unset` in scripts.
See the [configuration reference](docs/MANUAL.md#configuration) for machines, secrets, tariffs and integrations.

## Privacy and security

- Imports usage fields only. Conversation contents are not retained in the ledger, reports or cards.
- Does not read `~/.codex/auth.json` or Claude OAuth tokens. Quota queries use the official CLIs and their own login.
- API keys come from environment variables or a permissions-restricted `secrets.ini` (`600` on POSIX); they are excluded from logs, JSON, metrics and errors.
- The browser server and proxy listen on `127.0.0.1` by default. Cloud and admin API integrations use read-only queries.
- Usage and reports remain local unless you explicitly configure sharing, remote access or publishing. Dashboard views and full exports can include project and machine names; share cards omit them.

ComputAI checks for updates at most once a day. Disable this with `computai --set general.update_check=no`.
Source coverage and platform limitations are documented in the [beta release notes](docs/RELEASE-v0.1.0-beta.md#已知限制).

## Development features

This checkout includes beta.2 features that the released beta.1 does not yet provide:

| Feature | Entry point |
|---|---|
| Token breakdown and local request history | [Usage and tracing](docs/MANUAL.md#token-breakdown-and-local-request-tracing-beta2-development) |
| Personal history with monthly and annual reports | [Profile reports](docs/MANUAL.md#personal-history-profile-beta2-development) |
| Browser card creator and four new profile styles | [Cards below](#cards-and-sharing) |

## Cards and sharing

Export an SVG for your GitHub README with `computai --card --svg card.svg`.
The beta.2 creator (`computai --create`) lets you select a period and download PNG or SVG for social posts or READMEs.
Both use local usage aggregates. [First-card guide (繁中)](docs/MAKE-A-CARD.zh-TW.md).

Monthly recaps show source date coverage, record counts and comparison with the adjacent calendar month;
missing records remain unknown. Supported GUI logs and recorded local-model usage can share one recap;
web-only chat is outside this first version. The creator also exports aggregates for just the selected period as JSON.

<details>
<summary>Card gallery: all ten styles, layouts and export commands</summary>

### Choose your card style

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

#### Pick the look that fits your page

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

#### Make your first card

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

#### Adjust the layout and save your favourite

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
follow the [GitHub profile setup](#github-profile-updates).

</details>

### GitHub profile updates

```sh
computai --card --setup
```

The optional wizard configures your profile repository, writes the light/dark SVG pair and adds the README snippet.
Repository creation, pushing and background updates are choices in the setup.
For manual exports, use `--card --svg`; `--card --publish PATH` writes and commits the pair, and `--push` enables pushing.
See [profile setup](docs/MANUAL.md#github-profile-card-kept-fresh) and the [card reference](docs/MANUAL.md#profile-card).

## Development and feedback

```sh
tests/run.sh                      # unit tests; Python 3.8 also runs when available
python3 tests/e2e_ollama.py        # optional Ollama end-to-end test; requires qwen3:0.6b
```

Report problems through [GitHub issues](https://github.com/Sean-Hawks/computai/issues), including your version,
operating system, reproduction steps and `computai --doctor --redact` output.

## License and credits

[MIT](LICENSE). Machine sampling, GPU detection, web security headers and Prometheus output derive from
[slurmtop](https://github.com/Sean-Hawks/slurmtop), by the same author, at commit `84cd35d`.
