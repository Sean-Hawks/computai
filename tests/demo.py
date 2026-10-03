"""README 截圖用的示範資料：一本假的帳本（兩週的 Claude、Codex 用量和額度）加上 fixture 裡的假機器。
不是測試，不會被 unittest 找到（檔名不是 test_*）。

    python3 tests/demo.py DIR              # 在 DIR 建好設定檔和帳本，印出要 export 的環境變數
    python3 tests/demo.py DIR --web 8799   # 建好之後直接開網頁版

資料都是編的：專案叫 alpha、beta，機器是 tests/fixtures/machines 裡的 gpubox 和 mac。"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests import helpers  # noqa: E402

CONFIG = """[general]
lang = en

[plans]
claude = Claude Max 5x, 100, 2026-10-03
codex = ChatGPT Pro, 200, 2026-10-03

[machines]
gpubox = gpubox
mac = mac

[machine.gpubox]
services = vllm:8000
base_watts = 90

[machine.mac]
services = ollama:11434
idle_watts = 10
max_watts = 60
"""


def build(root):
    config, data = os.path.join(root, "config"), os.path.join(root, "data")
    os.makedirs(config, exist_ok=True)
    with open(os.path.join(config, "config.ini"), "w") as f:
        f.write(CONFIG)
    env = {"COMPUTAI_CONFIG_DIR": config, "COMPUTAI_DATA_DIR": data,
           "COMPUTAI_FIXTURES": helpers.fixture("machines"), "COMPUTAI_NO_UPDATE_CHECK": "1",
           "CLAUDE_CONFIG_DIR": os.path.join(root, "no-claude"), "CODEX_HOME": os.path.join(root, "no-codex")}
    os.environ.update(env)
    m = helpers.load()
    db = m.open_ledger()
    rnd = random.Random(7)
    t = time.time()
    rows = []
    for day in range(14):
        for i in range(rnd.randint(20, 60)):   # 一串間隔幾分鐘的請求
            ts = int(t - day * 86400 - rnd.randint(0, 10 * 3600))
            rows.append(dict(source="claude", uid="c%d-%d" % (day, i), ts=ts, model="claude-opus-5-5",
                             project=rnd.choice(["/home/demo/alpha", "/home/demo/beta"]),
                             input=rnd.randint(50, 400), output=rnd.randint(800, 9000),
                             cache_read=rnd.randint(40000, 160000), cache_write_5m=rnd.randint(0, 6000)))
        for i in range(rnd.randint(5, 25)):
            ts = int(t - day * 86400 - rnd.randint(0, 10 * 3600))
            rows.append(dict(source="codex", uid="x%d-%d" % (day, i), ts=ts, model="gpt-5.5",
                             project="/home/demo/beta", input=rnd.randint(5000, 30000),
                             cache_read=rnd.randint(20000, 90000), output=rnd.randint(500, 4000),
                             reasoning=rnd.randint(200, 2000)))
    m.add_usage(db, rows)
    # 另一台電腦（共用資料夾合併進來的）：一台正常、一台 3 小時沒回報
    for dev, name, age, k in (("demo-laptop", "laptop", 60, 40), ("demo-desk", "desk", 3 * 3600, 15)):
        m.add_usage(db, [dict(source="claude", uid="%s-%d" % (dev, i), ts=int(t - rnd.randint(0, 20 * 86400)),
                              model="claude-opus-5-5", project="gamma", output=rnd.randint(800, 6000),
                              cache_read=rnd.randint(20000, 90000), device=dev) for i in range(k)])
        m.note_device(db, dev, name=name, seen=int(t - age), via="folder", error="")
    for k in range(6):   # 最近一小時的額度樣本，看得出速度
        ts = int(t - (5 - k) * 600)
        m.add_limits(db, [dict(source="claude", name="5h", ts=ts, used_percent=30.0 + 3 * k, window_minutes=300,
                               resets_at=int(t + 2 * 3600)),
                          dict(source="claude", name="week", ts=ts, used_percent=41.0 + 0.2 * k, window_minutes=10080,
                               resets_at=int(t + 4 * 86400)),
                          dict(source="codex", name="week", ts=ts, used_percent=62.0 + 0.5 * k, window_minutes=10080,
                               resets_at=int(t + 3 * 86400)),
                          dict(source="codex", name="5h", ts=ts, used_percent=12.0, window_minutes=300,
                               resets_at=int(t + 3 * 3600))])
    for i in range(6):
        m._fx_calls.clear()
        m._fx_calls["gpubox"] = i % 2
        m.sample_machines(db)
    db.commit()
    db.close()
    return env


if __name__ == "__main__":
    root = os.path.abspath(sys.argv[1])
    env = build(root)
    if "--web" in sys.argv:
        port = sys.argv[sys.argv.index("--web") + 1]
        os.execvpe(sys.executable, [sys.executable, helpers.SCRIPT, "--web", "127.0.0.1:" + port],
                   dict(os.environ, **env))
    for k, v in sorted(env.items()):
        print("export %s=%s" % (k, v))
