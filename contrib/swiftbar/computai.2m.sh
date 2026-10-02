#!/bin/sh
# <xbar.title>ComputAI</xbar.title>
# <xbar.desc>Claude and Codex limits plus today's AI spend, from the ComputAI ledger.</xbar.desc>
# <xbar.dependencies>python3,computai</xbar.dependencies>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
#
# 放進 SwiftBar 的 plugin 資料夾；檔名裡的 2m 是每兩分鐘更新一次。
# SwiftBar 不會讀你的 shell 設定，所以這裡自己補 PATH。
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

computai --line --sep "  " 2>/dev/null || echo "ComputAI ?"
echo "---"
computai --summary --no-sync 2>/dev/null | sed 's/$/ | font=Menlo size=11/'
echo "---"
echo "Sync now | bash=computai param1=--sync terminal=false refresh=true"
