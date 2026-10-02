#!/bin/sh
# 用目前的 python3 和（如果有的話）Python 3.8 各跑一次全部測試。
cd "$(dirname "$0")/.." || exit 1
status=0
for py in python3 "${PY38:-$HOME/.local/share/uv/python/cpython-3.8-macos-aarch64-none/bin/python3.8}"; do
    command -v "$py" >/dev/null 2>&1 || continue
    out=$("$py" -m unittest discover -s tests -t . "$@" 2>&1) || { status=1; echo "$out" | tail -40; }
    printf '%s: %s\n' "$("$py" -c 'import sys; print(sys.version.split()[0])')" "$(echo "$out" | tail -1)"
done
exit $status
