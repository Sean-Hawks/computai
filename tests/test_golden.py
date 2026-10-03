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
        self.check("live-wide.txt", self.m.render_live(self.st, 170, theme_name="classic"))

    def test_narrow(self):
        self.check("live-narrow.txt", self.m.render_live(self.st, 90, theme_name="classic"))

    def test_compact(self):
        self.check("live-compact.txt", self.m.render_live(self.st, 90, height=20, theme_name="classic"))

    def test_ascii(self):
        self.check("live-ascii.txt", self.m.render_live(self.st, 90, ascii_=True, theme_name="classic"))

    def test_cyber(self):
        self.check("live-cyber.txt", self.m.render_live(self.st, 100, theme_name="cyber"))

    def test_hud_overview(self):
        self.check("live-hud.txt", self.m.render_live(self.st, 120, theme_name="cyber", height=40, view="overview"))

    def test_hud_views(self):
        for v in self.m.HUD_VIEWS:
            text = self.m.render_live(self.st, 160, theme_name="cyber", height=40, view=v)
            self.assertIn("1-5 switch tabs", text)
            self.assertTrue(all(self.m.vlen(ln) <= 160 for ln in text.splitlines()), v)
        ov = self.m.render_live(self.st, 120, theme_name="cyber", height=40, view="overview")
        self.assertLessEqual(len(ov.splitlines()), 40)                    # 總覽放得進一個畫面
        for name in ("MISSION CONTROL", "LIMITS", "THROUGHPUT", "ATTENTION REQUIRED", "NODES"):   # Minerva 的總控版面
            self.assertIn(name, ov)
        machines = self.m.render_live(self.st, 160, theme_name="cyber", height=40, view="machines")
        self.assertTrue(any("gpubox" in ln and "mac" in ln for ln in machines.splitlines()))   # 兩欄並排

    def test_cyber_color(self):
        # 有色碼的版本：cyber 的顏色依用途（docs/DESIGN.md）
        text = self.m.render_live(self.st, 100, color=True, theme_name="cyber")
        self.assertIn("38;2;251;191;36m\u25b2 WATCH", text)   # 總結列：琥珀色的狀態字（字＋記號，不用色塊）
        self.assertEqual(text.count("38;2;0;0;0;48;2;"), 0)         # Minerva：沒有黑字色底的字塊
        self.assertIn("\u2503", text)                                 # 額度量表上的時間標記
        self.assertIn("38;2;255;255;255m", text)         # 品牌色是白
        self.assertNotIn("\033[2m", text)                # 次要資訊用 meta 灰，不用 SGR 2
        self.assertNotIn("38;2;0;240;255m", text)        # 沒有飽和的青、洋紅
        self.assertNotIn("38;2;255;0;170m", text)
        st = dict(self.st, limits=[dict(r, used_percent=100.0) for r in self.st["limits"]])
        full = self.m.render_live(st, 100, color=True, theme_name="cyber")
        self.assertIn("38;2;248;113;113m\u25b2 ALERT", full)   # 額度用完：紅色「警告」
        self.m.set_style(theme="classic")

    def test_zh(self):
        self.m.set_lang("zh")
        self.check("live-zh.txt", self.m.render_live(self.st, 100, theme_name="classic"))
        self.m.set_lang("en")


if __name__ == "__main__":
    unittest.main()
