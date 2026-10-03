import json
import os
import time
import unittest

from tests import helpers

PRICES = {"claude-opus-5-5": {"input": 4.0, "output": 20.0, "cache_read": 0.2,
                              "cache_write_5m": 5.0, "cache_write_1h": 8.0}}
PLANS = {"claude": {"name": "Max", "usd": 100.0, "checked": ""}}


class Summary(unittest.TestCase):
    def setUp(self):
        if hasattr(time, "tzset"):  # Windows 沒有 tzset，日期邊界用本地時間也一樣能測
            os.environ["TZ"] = "UTC"
            time.tzset()
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)

    def test_cost_and_plan_ratio(self):
        start, end, label = self.m.month_range("2026-09")
        self.m.add_usage(self.db, [
            dict(source="claude", uid="1", ts=start + 10, model="claude-opus-5-5[1m]",
                 input=1000000, output=1000000, cache_read=1000000, cache_write_1h=1000000),
            dict(source="claude", uid="2", ts=end, model="claude-opus-5-5", input=1000000),  # 下個月
            dict(source="codex", uid="1", ts=start, model="gpt-x", input=5),
        ])
        s = self.m.summary(self.db, start, end, PRICES, PLANS, label)
        claude = s["sources"][0]
        self.assertAlmostEqual(claude["cost_usd"], 4 + 20 + 0.2 + 8)
        self.assertEqual(claude["plan"]["fee_in_range"], 100.0)
        self.assertAlmostEqual(claude["plan"]["value_ratio"], 0.32)
        self.assertEqual(s["unpriced_models"], ["gpt-x"])
        self.assertIn("No price for: gpt-x", self.m.render_summary(s))

    def test_explicit_cost_wins(self):
        self.m.add_usage(self.db, [dict(source="cloud", uid="1", ts=5, model="H100", cost_usd=3.5)])
        s = self.m.summary(self.db, 0, 10, PRICES, {})
        self.assertEqual(s["sources"][0]["cost_usd"], 3.5)
        self.assertEqual(s["unpriced_models"], [])

    def test_month_range(self):
        a, b, label = self.m.month_range("2026-12")
        self.assertEqual(label, "2026-12")
        self.assertEqual(b - a, 31 * 86400)

    def test_iso_ts(self):
        self.assertEqual(self.m.iso_ts("2026-09-17T10:56:05Z"), 1789642565)
        self.assertAlmostEqual(self.m.iso_ts("2026-09-17T10:56:05.7781234Z"), 1789642565.778123, 5)
        self.assertIsNone(self.m.iso_ts("nope"))


class Cli(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()

    def tearDown(self):
        self.sb.close()

    def test_empty_summary_json(self):
        r = self.sb.run("--summary", "--month", "2026-09", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertEqual(d["range"]["label"], "2026-09")
        self.assertEqual(d["sources"], [])
        self.assertTrue(os.path.exists(os.path.join(self.sb.data, "ledger.sqlite")))
        self.assertTrue(os.path.exists(os.path.join(self.sb.config, "prices.ini")))

    def test_bad_date(self):
        r = self.sb.run("--summary", "--since", "yesterday")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("YYYY-MM-DD", r.stderr)


if __name__ == "__main__":
    unittest.main()


class Breakdown(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)
        self.m.add_usage(self.db, [
            dict(source="claude", uid="1", ts=100, model="claude-opus-5-5", project="/a/專案", output=1000000),
            dict(source="claude", uid="2", ts=200, model="claude-opus-5-5", project="/a/專案", input=1000000,
                 subagent=1),
            dict(source="claude", uid="3", ts=86400 * 3, model="claude-opus-5-5", project="/b/other", input=1),
        ])

    def test_by_project(self):
        g = self.m.breakdown(self.db, 0, 86400 * 10, "project", PRICES)
        self.assertEqual(g[0]["project"], "/a/專案")
        self.assertEqual(g[0]["requests"], 2)
        self.assertEqual(g[0]["subagent_requests"], 1)
        self.assertAlmostEqual(g[0]["cost_usd"], 24.0)
        text = self.m.render_breakdown(g, "project")
        self.assertIn("a/專案", text)
        # 全形字算兩格，欄位仍然對齊
        lines = text.splitlines()
        self.assertEqual(self.m.vlen(lines[1]), self.m.vlen(lines[2]))

    def test_by_day_sorted(self):
        g = self.m.breakdown(self.db, 0, 86400 * 10, "day", PRICES)
        self.assertEqual(len(g), 2)
        self.assertLess(g[0]["day"], g[1]["day"])

    def test_cell_tail(self):
        self.assertEqual(self.m.cell("abcdef", 3, tail=True), "def")
        self.assertEqual(self.m.cell("專案", 3), "專 ")


class TerminalSafety(unittest.TestCase):
    def test_escape_sequences_in_project_names_are_stripped(self):
        sb = helpers.Sandbox()
        try:
            os.makedirs(sb.data)
            m = helpers.load()
            os.environ["COMPUTAI_DATA_DIR"] = sb.data
            db = m.open_ledger()
            m.add_usage(db, [dict(source="claude", uid="1", ts=1789000000, model="claude-opus-5-5",
                                  project="/x/\x1b]52;c;ZXZpbA==\x07evil", output=1)])
            db.commit()
            db.close()
            r = sb.run("--summary", "--month", "2026-09", "--by", "project", "--no-sync")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("\x1b", r.stdout)
            self.assertNotIn("\x07", r.stdout)
            self.assertIn("evil", r.stdout)
            j = sb.run("--summary", "--month", "2026-09", "--by", "project", "--no-sync", "--json")
            self.assertNotIn("\x1b", j.stdout)
        finally:
            os.environ.pop("COMPUTAI_DATA_DIR", None)
            sb.close()


class Csv(unittest.TestCase):
    def test_export(self):
        import csv
        m = helpers.load()
        sb = helpers.Sandbox()
        try:
            os.makedirs(sb.root, exist_ok=True)
            db = m.open_ledger(":memory:")
            m.add_usage(db, [dict(source="claude", uid="1", ts=100, model="claude-opus-5-5", project="=cmd|x",
                                  output=1000000),
                             dict(source="claude", uid="2", ts=10 ** 9, model="claude-opus-5-5", output=1)])
            path = os.path.join(sb.root, "u.csv")
            self.assertEqual(m.export_csv(db, 0, 1000, path, PRICES), 1)
            with open(path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]["project"], "'=cmd|x")     # 不讓試算表當成公式
            self.assertEqual(float(rows[0]["cost_usd"]), 20.0)
            self.assertEqual(rows[0]["output"], "1000000")
            db.close()
        finally:
            sb.close()


class Lab(unittest.TestCase):
    def test_totals_and_lab(self):
        m = helpers.load()
        sb = helpers.Sandbox()
        try:
            os.makedirs(sb.root, exist_ok=True)
            db = m.open_ledger(":memory:")
            m.add_usage(db, [dict(source="claude", uid="1", ts=100, model="claude-opus-5-5",
                                  project="/secret/thesis", output=1000000)])
            t = m.totals(db, 0, 1000, "2026-09", "alice")
            self.assertNotIn("secret", json.dumps(t))               # 不帶專案名稱
            self.assertEqual(t["sources"]["claude"]["tokens"], 1000000)
            folder = os.path.join(sb.root, "lab")
            os.makedirs(folder)
            for who, cost in (("alice", 20.0), ("bob", 5.5)):
                d = dict(t, who=who, total_cost_usd=cost)
                d["sources"] = {"claude": dict(t["sources"]["claude"], cost_usd=cost)}
                with open(os.path.join(folder, who + ".json"), "w") as f:
                    json.dump(d, f)
            with open(os.path.join(folder, "junk.json"), "w") as f:
                f.write("{not json")
            rows, total, srcs = m.lab(folder)
            self.assertEqual([r["who"] for r in rows], ["alice", "bob"])
            self.assertEqual(total["sources"]["claude"]["cost_usd"], 25.5)
            self.assertIn("total", m.render_lab(rows, total, srcs))
            db.close()
        finally:
            sb.close()
