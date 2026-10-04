# One-line display / 一行顯示

`computai --line` prints one line such as

    Claude 42%｜Codex 100% (1d0h)｜today $6.9

- **Claude / Codex %**: the most used limit window of each subscription. When a window is at 90% or
  more, the time until it resets is shown in brackets. A window whose reset time has passed counts as 0%.
- **today**: the API-equivalent cost of everything recorded today (local time).
- `--sep " | "` changes the separator, `--json` gives the same data as JSON.
- `--line` re-reads the logs at most every 30 seconds, so it is cheap to call often.

Codex limits come from the Codex session logs. Claude limits only exist in the JSON that Claude Code
passes to its status line, so they appear once `computai --statusline` has run at least once
(Claude Pro/Max accounts only).

## Claude Code status line

`~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "computai --statusline"
  }
}
```

`--statusline` reads `rate_limits.five_hour` and `rate_limits.seven_day` from stdin, stores them in the
ledger. In beta.2 development it also shows the model, live context window, last request's uncached input,
cache reads/writes, output and input cache-hit ratio, plus reset countdowns. `--statusline-view compact`
keeps the original single line. `--line` itself stays unchanged.

These fields come from Claude Code's native stdin payload; no transcript is opened. Context counts
are for the latest context window, **not cumulative session usage**, and exclude output when calculating
context occupancy. Missing values are `?`. Context/last-request numbers are displayed, not added to the
usage ledger; only limit snapshots are stored. Width uses Claude's `COLUMNS` and wraps when needed.
See [Claude Code's official fields](https://code.claude.com/docs/en/statusline), verified 2026-10-04.

Try it with the synthetic fixture (no API request):

```sh
COMPUTAI_DATA_DIR="$(mktemp -d)" computai --statusline --no-sync --lang zh < tests/fixtures/statusline/detailed.json
```

The temporary data directory keeps synthetic limits out of your real ledger. The fixture's rate-limit dates are fixed; its model/context/request numbers remain useful for a preview.
Use `--setup` to review an integration and preserve an existing status line, or merge the configuration
above into your settings rather than replacing unrelated settings.

If you already have a status line script, keep it and feed the same input to ComputAI:

```sh
#!/bin/sh
input=$(cat)
mine=$(printf '%s' "$input" | your-existing-statusline)
printf '%s  %s\n' "$mine" "$(printf '%s' "$input" | computai --statusline)"
```

## tmux

```tmux
set -g status-interval 60
set -g status-right '#(computai --line --sep " · ")'
```

## SwiftBar / xbar (macOS menu bar)

Copy [`contrib/swiftbar/computai.2m.sh`](../contrib/swiftbar/computai.2m.sh) into your SwiftBar plugin
folder and make it executable. The menu bar shows the line; the drop-down shows this month's summary.

---

## 中文說明

`computai --line` 輸出一行：每個訂閱最吃緊的額度視窗使用率（90% 以上會附重置倒數），加上今天的等值 API 花費。
Codex 的額度從 log 讀；Claude 的額度只有 Claude Code 傳給 statusline 的 JSON 裡有，所以要把
`computai --statusline` 設成 Claude Code 的 statusLine 指令（設定方式見上面），跑過一次之後
`--line`、tmux、SwiftBar 才看得到 Claude 的百分比（限 Pro/Max 帳號）。
beta.2 開發版的 `--statusline` 另顯示模型、目前上下文進度、上次請求的新輸入／快取讀寫／輸出、輸入命中率及重置倒數。
上下文不是 session 累計，缺少欄位顯示 `?`；模型與當次用量只顯示、不再入帳，仍只保存額度快照。
不讀 transcript、提示詞或回應。加 `--statusline-view compact` 保留原本單行；`--line` 維持不變。
可用上面的合成 fixture 先預覽；既有 Claude settings 整合用 `--setup` 檢視差異，或合併 statusLine 欄位。
