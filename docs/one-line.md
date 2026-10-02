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
ledger, and prints the same line as `--line`. It ignores every other field in the payload.

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
`--statusline` 只讀 `rate_limits`，其他欄位一概不看。
