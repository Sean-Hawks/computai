# ComputAI

**Where your compute and AI money goes.** A terminal dashboard and browser GUI for AI usage,
subscription limits, local inference and compute costs. Track Claude, Codex, your homelab and
cloud GPUs in one ledger: tokens, GPU hours, kWh and money.

Single Python file · Standard library only · Python 3.8+ · macOS, Linux and Windows

[繁體中文](README.zh-TW.md) · [Quick start](#quick-start) · [Manual](docs/MANUAL.md) · [Release notes](docs/RELEASE-v0.1.0-beta.2.md)

**Current release:** [v0.1.0-beta.2](https://github.com/Sean-Hawks/computai/releases/tag/v0.1.0-beta.2).
Features marked **unreleased development** are available on the [development branch](https://github.com/Sean-Hawks/computai/tree/docs-card-gallery), not in the released beta.2 or `main`.
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
curl -fsSL https://raw.githubusercontent.com/Sean-Hawks/computai/v0.1.0-beta.2/install.sh | sh
```

Windows — download and extract the ZIP from the [release page](https://github.com/Sean-Hawks/computai/releases/tag/v0.1.0-beta.2), then run in that folder:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

Ensure the install directory is on `PATH`; on Windows, reopen your terminal after installation.
To install a source checkout, run `sh install.sh` on macOS/Linux or the PowerShell command above on Windows.
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
Source coverage and platform limitations are documented in the [beta release notes](docs/RELEASE-v0.1.0-beta.2.md#驗證與限制).

## Development features

The [development branch](https://github.com/Sean-Hawks/computai/tree/docs-card-gallery) includes unreleased features that the released beta.2 and `main` do not yet provide:

| Feature | Entry point |
|---|---|
| Token breakdown and local request history | [Usage and tracing](https://github.com/Sean-Hawks/computai/blob/docs-card-gallery/docs/MANUAL.md#token-breakdown-and-local-request-tracing-beta2-development) |
| Personal history with monthly and annual reports | [Profile reports](https://github.com/Sean-Hawks/computai/blob/docs-card-gallery/docs/MANUAL.md#personal-history-profile-beta2-development) |
| Browser card creator and four new profile styles | [Cards below](#cards-and-sharing) |

## Cards and sharing

Create a usage card for your README, portfolio or social posts. Choose the design by its layout and the information you want to share.
Cards use local aggregates and omit conversations, project paths and machine names.

| Design | Best for | Default format | Command | Available in |
|---|---|---|---|---|
| **Minimal** | A concise README banner with key totals | `compact` · 720×230 | `--card --card-style minimal` | unreleased development |
| **Paper** | A vertical summary with serif typography | `portrait` · 420×610 | `--card --card-style paper` | unreleased development |
| **GitHub** | Statistics, activity grid and model shares | `dashboard` · 900×360 | `--card --card-style github` | unreleased development |
| **Terminal** | A console-style banner with monospace text | `compact` · 720×230 | `--card --card-style terminal` | unreleased development |
| **HUD** | A detailed profile with agent activity, rank and badges | `hud` · 900×390 | `--card --card-style netrunner` | beta.1 |
| **Web/TUI sharing card** | Social posts, monthly recaps or a README image | Square, portrait, wide or README | `--create` · PNG/SVG downloads | unreleased development |

<details>
<summary>Preview the six designs (demo data)</summary>

| Minimal · concise banner | Terminal · console banner |
|---|---|
| ![Minimal profile card](docs/images/card-minimal.svg) | ![Terminal profile card](docs/images/card-terminal.svg) |
| **GitHub · activity dashboard** | **HUD · detailed agent profile** |
| ![GitHub profile card](docs/images/card-github.svg) | ![HUD profile card](docs/images/card-netrunner.svg) |
| **Paper · vertical summary** | **Web/TUI · social sharing** |
| <img src="docs/images/card-paper.svg" width="240" alt="Paper card with serif typography and a vertical activity grid"> | <img src="docs/images/share-preview.png" width="240" alt="Web/TUI sharing card with usage totals and a daily activity chart"> |

</details>

### Export a card

From the [unreleased development checkout](https://github.com/Sean-Hawks/computai/tree/docs-card-gallery) with Python 3.8+, run:

```sh
python3 ./computai --create                         # choose a period and download PNG/SVG
python3 ./computai --card --card-style minimal --svg card.svg
python3 ./computai --card --card-style paper --svg card.svg
```

On Windows, replace `python3 ./computai` with `py -3 computai`; after installation, use `computai`.
Add the exported SVG to your README:

```markdown
![My AI usage](card.svg)
```

The creator uses the Web/TUI design; the five profile designs use `--card` and export SVG.
Share the downloaded image; the creator HTML contains selectable history.
[First-card guide (繁中)](https://github.com/Sean-Hawks/computai/blob/docs-card-gallery/docs/MAKE-A-CARD.zh-TW.md).

### Layout options

In unreleased development, `--card-layout` accepts `auto` (follow the style), `compact`, `portrait`, `dashboard` or `hud`.
Compact banners show key totals; dashboard and portrait add activity grids and hours.
The HUD design includes the fuller agent profile with decorative animation; the other profile designs are static by default.

```sh
computai --card --card-style github --card-layout compact --svg card.svg
computai --set card.style=paper --set card.layout=portrait  # save defaults for exports and daily updates
```

Every profile design supports light/dark mode (`--card-theme`) and English/Traditional Chinese labels.
The HUD colour presets are `netrunner` (default), `arasaka`, `militech`, `amber`, `matrix` and `synthwave`;
they share the same layout. To compare all presets and layouts locally, use `computai --card --html styles.html` (unreleased development).
Display names, custom accents and other options are in the [card reference](docs/MANUAL.md#profile-card).

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
