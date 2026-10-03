# ComputAI

**Where your compute and AI money goes.** One ledger for your Claude and ChatGPT
subscriptions, the local models on your homelab, the machines they run on and the cloud
GPUs you rent: tokens, GPU hours, kWh and money, side by side.

[繁體中文說明](README.zh-TW.md) · [Manual](docs/MANUAL.md) · [使用手冊](docs/MANUAL.zh-TW.md)

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

![Live terminal dashboard](docs/images/live.png)

`computai --web` gives the same view in a browser (phone layout included):

![Web dashboard](docs/images/web.png)

*(Screenshots use demo data.)*

## What it does

| | Source | What you get |
|---|---|---|
| **Subscriptions** | Claude Code and Codex session logs on this computer | tokens per model, cache and reasoning shown separately, cost at API prices versus your monthly fee, per-project breakdown, Codex and Claude limit windows with reset countdowns |
| **API** | Anthropic and OpenAI admin usage APIs (optional) | organisation usage per model and day |
| **Local models** | Ollama, llama.cpp, vLLM, SGLang, LM Studio, OpenAI-compatible servers | which models are loaded, tokens (from `/metrics`, or from the optional `--proxy` for Ollama), "model loaded but idle" alerts |
| **Machines** | SSH + `sh` (nothing to install), or this computer | CPU, GPU, power, kWh, electricity cost, AI share of the time, joules per token |
| **Cloud GPUs** | RunPod, Vast.ai, Lambda (read-only API calls) | what is running, what it costs per hour, and **GPUs that sit idle while still billing** |

On top of the ledger: cache-efficiency analysis (which sessions keep re-writing the prompt
cache and what that cost), a month-end forecast with an optional budget, a plan simulator,
a GPU payback calculator and time-of-use electricity prices (Taipower two-tier presets).

Also: `--discover` finds machines in `~/.ssh/config` and Tailscale; each machine shows how large a model
still fits; smart plugs (Shelly, Tasmota, Home Assistant) give measured power; `--wake` sends Wake-on-LAN;
`--mcp` lets agents ask about their own budget; `--weekly --send` posts a weekly summary to Discord or
Telegram; `--recap` makes a year-in-review card; `--csv` exports records; `--totals`/`--lab` combine a
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

## Use

```sh
computai                          # live dashboard: compute, AI usage, alerts (q to quit)
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
computai --once --lang zh         # 中文、印一次
```

Every command takes `--json`. The first run writes `config.ini` and `prices.ini` to
`~/.config/computai/` (see `computai --paths`); edit them to set your plans, machines,
electricity price and API prices. Every price carries the date it was checked.

Status bars: `computai --line` for tmux and SwiftBar, `computai --statusline` as Claude Code's
status line (that is also how ComputAI learns Claude's limit percentages). See
[docs/one-line.md](docs/one-line.md).

## Privacy and security

- Reads only usage fields from your logs. Prompts and responses are never read into the
  ledger, stored or sent anywhere. `~/.codex/auth.json` and Claude's OAuth tokens are never read.
- API keys come from environment variables or a `chmod 600` `secrets.ini`, and never appear in
  logs, `--json`, `/metrics` or error messages.
- `--web` and `--proxy` listen on `127.0.0.1` unless you say otherwise; the web server rejects
  requests for other host names (DNS rebinding).
- Cloud and admin APIs are only ever called with read-only "list" requests.

## Tests

```sh
tests/run.sh                    # unit tests on python3 and, if present, Python 3.8
python3 tests/e2e_ollama.py     # end-to-end: real Ollama behind the proxy (needs ollama + qwen3:0.6b)
```

## Credits

Machine sampling, GPU detection, the web server's security headers and the Prometheus
output are ported from [slurmtop](https://github.com/Sean-Hawks/slurmtop) (MIT, same author,
commit 84cd35d). MIT licence.
