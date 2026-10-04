#!/bin/sh
# ComputAI installer for macOS and Linux.
#
#   sh install.sh                # install to ~/.local/bin
#   PREFIX=/usr/local sh install.sh
#
# Run from a checkout to install that copy; otherwise the script is downloaded from
# COMPUTAI_URL. Nothing runs in the background and nothing outside PREFIX is touched,
# except the config and ledger folders ComputAI creates on its first run.
set -eu

PREFIX="${PREFIX:-$HOME/.local}"
BIN="$PREFIX/bin"
REF="${COMPUTAI_REF:-v0.1.0-beta.1}"
URL="${COMPUTAI_URL:-https://raw.githubusercontent.com/Sean-Hawks/computai/$REF/computai}"
HERE=$(cd "$(dirname "$0")" && pwd)

PY=""
for p in python3 python; do
    if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
        PY=$p
        break
    fi
done
if [ -z "$PY" ]; then
    echo "computai needs Python 3.8 or newer (python3 not found)." >&2
    exit 1
fi

mkdir -p "$BIN"
tmp="$BIN/.computai.$$"
trap 'rm -f "$tmp"' EXIT
if [ -f "$HERE/computai" ]; then
    cp "$HERE/computai" "$tmp"
elif command -v curl >/dev/null 2>&1; then
    curl -fsSL "$URL" -o "$tmp"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$tmp" "$URL"
else
    echo "need curl or wget to download $URL" >&2
    exit 1
fi
head -1 "$tmp" | grep -q python || { echo "download did not look like computai" >&2; exit 1; }
chmod 755 "$tmp"
mv "$tmp" "$BIN/computai"
trap - EXIT

echo "installed $BIN/computai ($("$BIN/computai" --version))"
case ":$PATH:" in
    *":$BIN:"*) ;;
    *) echo "add $BIN to your PATH, e.g.: echo 'export PATH=\"$BIN:\$PATH\"' >> ~/.profile" ;;
esac
echo "next: computai --summary --month    (config: $("$BIN/computai" --paths | sed -n 's/^config: //p'))"
