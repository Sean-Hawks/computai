# ComputAI v0.1.0-beta（草稿，等作者確認後才發佈）

> **Where your compute and AI money goes.** One ledger for your Claude and ChatGPT subscriptions,
> local models, homelab machines and rented cloud GPUs.

This is the first public beta. It is one Python file (3.8+, standard library only) that runs on macOS,
Linux and Windows. Watched machines only need SSH and `sh`.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/Sean-Hawks/computai/main/install.sh | sh
computai            # live dashboard; the first run asks one question about your plan
computai --doctor   # what is detected, and the command that fixes each gap
```

Windows: `powershell -ExecutionPolicy Bypass -File install.ps1`.

## What's in it

- **Subscriptions**: Claude Code and Codex logs → tokens per model (cache and reasoning shown separately),
  per project, at API prices versus your monthly fee. Account-wide limits come from the official
  `claude` and `codex` CLIs (no tokens read, no quota used). Checks follow the burn rate: every 10 minutes
  when calm, down to every minute while a limit burns, and 30 seconds after a reset.
- **Local models**: Ollama, llama.cpp, vLLM, SGLang, LM Studio; an optional `--proxy` counts Ollama tokens;
  "loaded but idle" alerts.
- **Machines**: CPU, GPU, power, kWh and electricity cost over SSH; Taipower time-of-use presets; smart plugs.
- **Cloud GPUs**: RunPod, Vast.ai, Lambda (read-only), with "idle but still billing" alerts.
- **Analysis**: cache efficiency, month-end forecast and budget, plan simulator, GPU payback.
- **Views**: terminal dashboard, `--web` (phone layout), `/metrics`, `--html` reports, a one-line status
  for Claude Code / tmux / SwiftBar, `--wrapped`, a GitHub profile card, an MCP server.

## New in the beta

- The first run explains every empty spot: where it looked for logs, how to connect limits, and one
  question per subscription with a plan guessed from the logs.
- `computai --doctor --redact` for bug reports: machine names, hosts, IPs, project names and home paths
  become codes.
- Update check, at most once a day (`[general] update_check = no` turns it off). Only the version line of
  `computai` on GitHub is read; nothing about you is sent.
- Usage from your other computers: a shared folder (iCloud, Dropbox, Syncthing) or SSH pull, usage numbers only
  (docs/MULTI-DEVICE.md).
- Limit checks follow the burn rate (`[limits] refresh = adaptive|fixed`); `--doctor` shows the next check and why.

## Privacy

Only usage fields are read from logs; prompts and responses are never stored or sent. `~/.codex/auth.json`
and Claude's OAuth tokens are never read. The web server and proxy listen on `127.0.0.1` by default.

## Known gaps

- Windows has been tested less than macOS and Linux.
- Claude's plan can't be read from anywhere local, so the first-run plan is a guess you confirm.

Found a bug? Open an issue and paste `computai --doctor --redact`.
