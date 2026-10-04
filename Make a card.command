#!/bin/sh
# macOS：從下載／解壓的 ComputAI 資料夾雙擊，不需要安裝或設定 PATH。
cd "$(dirname "$0")" || exit 1
for creator_python in python3 python; do
    if command -v "$creator_python" >/dev/null 2>&1 && "$creator_python" -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>/dev/null; then
        "$creator_python" ./computai recap --lang zh
        creator_status=$?
        if [ "$creator_status" -ne 0 ]; then
            printf '\n無法開啟製卡頁。按 Enter 關閉。\n'
            read -r creator_reply
        fi
        exit "$creator_status"
    fi
done
printf '需要 Python 3.8 或更新版：請先從 https://www.python.org/downloads/ 安裝。\n按 Enter 關閉。\n'
read -r creator_reply
exit 1
