#!/bin/sh
# 在乾淨的 Linux 容器裡跑一次安裝和全部測試：python:3.8-slim（最舊支援的 Python）和 ubuntu（系統的 python3）。
#   sh tests/docker.sh            # 兩個都跑
#   sh tests/docker.sh ubuntu     # 只跑一個
cd "$(dirname "$0")/.." || exit 1
status=0
for image in ${*:-python:3.8-slim ubuntu:24.04}; do
    case $image in
        ubuntu*) prep="apt-get update -qq >/dev/null && apt-get install -y -qq python3 >/dev/null" ;;
        *) prep="true" ;;
    esac
    echo "== $image"
    docker run --rm -v "$PWD:/src:ro" "$image" sh -c "
        set -eu
        $prep || exit 1
        cp -R /src /work
        cd /work
        rm -rf tests/__pycache__ __pycache__
        sh install.sh
        export PATH=\$HOME/.local/bin:\$PATH
        computai --version
        computai --once >/dev/null
        computai --doctor --redact --no-sync >/dev/null
        test_log=\$(mktemp)
        test_status=0
        python3 -m unittest discover -s tests -t . > \"\$test_log\" 2>&1 || test_status=\$?
        tail -12 \"\$test_log\"
        rm -f \"\$test_log\"
        exit \$test_status
    " || status=1
done
exit $status
