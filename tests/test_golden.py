"""live 畫面的 golden 測試：固定的假資料畫出來要跟 tests/golden/ 裡的檔案一字不差。
改了介面、確定新的畫面是對的，就用 COMPUTAI_UPDATE_GOLDEN=1 重跑一次更新檔案。"""
import os
import unittest

from tests import helpers

GOLDEN = os.path.join(helpers.ROOT, "tests", "golden")
NOW = 1790000000


def build_state(m, db):
    m.add_usage(db, [
        dict(source="claude", uid="1", ts=NOW - 3600, model="claude-opus-5-5", project="/p/x", output=500000,
             cache_read=2000000),
        dict(source="claude", uid="2", ts=NOW - 86400 * 3, model="claude-opus-5-5", project="/p/x", output=200000),
        dict(source="codex", uid="3", ts=NOW - 7200, model="gpt-5.5", project="/p/y", input=100000, output=20000),
    ])
    m.add_limits(db, [dict(source="claude", name="5h", ts=NOW - 60, used_percent=42.0, window_minutes=300,
                           resets_at=NOW + 7800),
                      dict(source="codex", name="week", ts=NOW - 60, used_percent=93.0, window_minutes=10080,
                           resets_at=NOW + 30000)])
    for i in range(6):
        os.environ["COMPUTAI_FAKE_NOW"] = str(NOW - (6 - i) * 60)
        m._fx_calls.clear()
        m._fx_calls["gpubox"] = i % 2
        m.sample_machines(db)
    os.environ["COMPUTAI_FAKE_NOW"] = str(NOW)
    st = m.clean_strings(m.dashboard_state(db))
    st["insights"] = [{"kind": "plan", "text": "Codex: example advice"}]
    return st


class Golden(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.makedirs(self.sb.config)
        with open(os.path.join(self.sb.config, "config.ini"), "w") as f:
            f.write("[machines]\ngpubox = gpubox\nmac = mac\n\n[machine.gpubox]\nservices = vllm:8000\n"
                    "base_watts = 90\n\n[machine.mac]\nservices = ollama:11434\nidle_watts = 10\nmax_watts = 60\n")
        os.environ.update(COMPUTAI_CONFIG_DIR=self.sb.config, COMPUTAI_DATA_DIR=self.sb.data, TZ="UTC",
                          COMPUTAI_FIXTURES=helpers.fixture("machines"))
        if hasattr(__import__("time"), "tzset"):
            __import__("time").tzset()
        self.m = helpers.load()
        self.db = self.m.open_ledger()
        self.st = build_state(self.m, self.db)

    def tearDown(self):
        self.db.close()
        os.environ.clear()
        os.environ.update(self.old)
        if hasattr(__import__("time"), "tzset"):
            __import__("time").tzset()
        self.sb.close()

    def check(self, name, text):
        path = os.path.join(GOLDEN, name)
        if os.environ.get("COMPUTAI_UPDATE_GOLDEN") or not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(text, f.read(), "%s changed; rerun with COMPUTAI_UPDATE_GOLDEN=1 if intended" % name)

    def test_wide(self):
        self.check("live-wide.txt", self.m.render_live(self.st, 170))

    def test_narrow(self):
        self.check("live-narrow.txt", self.m.render_live(self.st, 90))

    def test_compact(self):
        self.check("live-compact.txt", self.m.render_live(self.st, 90, height=20))

    def test_ascii(self):
        self.check("live-ascii.txt", self.m.render_live(self.st, 90, ascii_=True))

    def test_zh(self):
        self.m.set_lang("zh")
        self.check("live-zh.txt", self.m.render_live(self.st, 100))
        self.m.set_lang("en")


if __name__ == "__main__":
    unittest.main()
