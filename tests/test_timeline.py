import os
import time
import unittest

from tests import helpers

DAY = 1790035200 - 1790035200 % 86400   # 某一天的 00:00 UTC
NOW = DAY + 15 * 3600                    # 下午 3 點


def ev(uid, ts, session="s1", source="claude", sub=0, device="", project="/w/alpha", model="claude-opus-5-5", out=1000):
    return {"source": source, "uid": uid, "ts": ts, "session": session, "subagent": sub, "device": device,
            "project": project, "model": model, "output": out}


class Timeline(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(self.sb.env(TZ="UTC", COMPUTAI_FAKE_NOW=str(NOW)))
        if hasattr(time, "tzset"):
            time.tzset()
        self.m = helpers.load()
        self.m.set_lang("en")
        self.m.set_style(False, False)
        self.db = self.m.open_ledger()
        rows = [ev("y1", DAY - 600)]                                           # 昨天 23:50 開始的 session
        rows += [ev("a%d" % i, DAY + 600 + i * 120) for i in range(10)]        # 00:10 起連續 20 分鐘
        rows += [ev("a-late", DAY + 3600)]                                     # 空等 22 分鐘後又來一個
        rows += [ev("sub%d" % i, DAY + 900 + i * 60, sub=1, out=500) for i in range(5)]   # subagent
        rows += [ev("b%d" % i, DAY + 14 * 3600 + i * 60, session="s2", source="codex", project="/w/beta",
                    model="gpt-5.5", out=3000) for i in range(30)]               # 14:00 另一台電腦上的 Codex
        for r in rows[-30:]:
            r["device"] = "dev-laptop"
        rows += [ev("c%d" % i, DAY + 14 * 3600 + 300 + i * 60, session="s3", out=2000) for i in range(10)]
        rows += [{"source": "local", "uid": "l%d" % i, "ts": DAY + 14 * 3600 + i * 90, "project": "gpubox",
                  "model": "qwen3:8b", "session": "proxy", "output": 400} for i in range(8)]
        self.m.add_usage(self.db, rows)
        self.m.note_device(self.db, "dev-laptop", name="laptop", seen=NOW)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        os.environ.clear()
        os.environ.update(self.old)
        if hasattr(time, "tzset"):
            time.tzset()
        self.sb.close()

    def test_rows_and_moments(self):
        tl = self.m.timeline_data(self.db, prices={})
        labels = [(r["source"], r["label"], r["subagent"], r["continued"]) for r in tl["rows"]]
        self.assertEqual(labels[0], ("claude", "alpha", False, True))         # 跨午夜：標成從昨天接續
        self.assertEqual(labels[1][:3], ("claude", "alpha", True))              # subagent 掛在主 session 底下
        self.assertIn(("codex", "beta@laptop", False, False), labels)          # 別台電腦
        self.assertIn(("local", "qwen3:8b@gpubox", False, False), labels)       # 本地模型、機器
        self.assertNotIn(DAY - 600, [ts for r in tl["rows"] for ts, _ in r["events"]])   # 昨天的請求不畫
        st = tl["stats"]
        self.assertEqual(st["peak"], 3)                                         # 14:05 左右 codex、claude、本地同時
        self.assertEqual(st["longest"]["seconds"], 29 * 60)                    # codex 的 30 分鐘
        self.assertEqual(st["idle"], {"seconds": 3600 - (600 + 9 * 120), "start": DAY + 600 + 9 * 120})

    def test_narrow_terminal(self):
        tl = self.m.timeline_data(self.db, prices={})
        for width in (60, 100, 160):
            lines = self.m.render_timeline(tl, width)
            self.assertTrue(all(self.m.vlen(ln) <= width for ln in lines), (width, [ln for ln in lines if self.m.vlen(ln) > width]))
        text = "\n".join(self.m.render_timeline(tl, 60))
        self.assertIn("Today your agents worked", text)
        self.assertIn("subagents", text)
        self.assertIn("longest wait: 32m from 00:28", text)
        self.assertIn("\u21b6claude alpha", text)                              # 從昨天接續的記號

    def test_svg_has_no_project_or_machine_names(self):
        svg = self.m.render_timeline_svg(self.m.timeline_data(self.db, prices={}))
        self.assertTrue(svg.startswith("<svg"))
        __import__("xml.etree.ElementTree").etree.ElementTree.fromstring(svg)   # 是合法的 XML
        for name in ("alpha", "beta", "laptop", "gpubox", "/w/"):
            self.assertNotIn(name, svg)
        self.assertIn("Claude 1", svg)
        self.assertIn("qwen3:8b", svg)

    def test_tab_in_live_view(self):
        st = self.m.dashboard_state(self.db)
        text = self.m.render_live(st, 60, theme_name="cyber", height=30, view="timeline")
        self.assertIn("TIMELINE", text)
        self.assertTrue(all(self.m.vlen(ln) <= 60 for ln in text.splitlines()))


if __name__ == "__main__":
    unittest.main()
