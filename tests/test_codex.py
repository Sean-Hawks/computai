import json
import os
import unittest

from tests import helpers

HOME = helpers.fixture("codex")
NEW = os.path.join(HOME, "sessions", "2026", "09", "10", "rollout-2026-09-10T00-00-00-s-new.jsonl")
OLD = os.path.join(HOME, "archived_sessions", "rollout-2026-09-09T00-00-00-s-old.jsonl")


class CodexParser(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()

    def test_new_format(self):
        rows, limits = self.m.parse_codex_file(NEW)
        self.assertEqual(len(rows), 2)
        a, b = rows
        self.assertEqual((a["input"], a["cache_read"], a["output"], a["reasoning"]), (8000, 12000, 300, 80))
        self.assertEqual((b["input"], b["cache_read"], b["cache_write_5m"]), (5000, 25000, 1000))
        self.assertEqual(a["model"], "gpt-5.5")
        self.assertEqual(a["session"], "s-new")
        self.assertEqual(a["project"], "/home/demo/beta")
        self.assertEqual(len(limits), 4)
        last = [l for l in limits if l["name"] == "5h"][-1]
        self.assertEqual((last["used_percent"], last["window_minutes"], last["plan"]), (43.5, 300, "pro"))
        self.assertNotIn("FAKE", json.dumps(rows) + json.dumps(limits))

    def test_old_format_skips_repeats(self):
        rows, limits = self.m.parse_codex_file(OLD)
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(r["input"] + r["cache_read"] for r in rows), 3000)
        self.assertEqual(sum(r["output"] for r in rows), 250)
        self.assertEqual(rows[1]["cache_read"], 1500)
        self.assertEqual(rows[0]["model"], "gpt-6-astra")
        self.assertEqual(max(l["used_percent"] for l in limits if l["name"] == "week"), 12.0)


class Limits(unittest.TestCase):
    def test_current_limits(self):
        m = helpers.load()
        db = m.open_ledger(":memory:")
        self.addCleanup(db.close)
        _, limits = m.parse_codex_file(NEW)
        m.add_limits(db, limits)
        m.add_limits(db, [dict(source="codex", name="old", ts=1000, used_percent=5.0)])
        cur = {r["name"]: r for r in m.current_limits(db, t=1789690000)}
        self.assertEqual(sorted(cur), ["5h", "week"])          # 太舊的視窗不顯示
        self.assertEqual(cur["5h"]["used_percent"], 43.5)
        self.assertEqual(cur["5h"]["resets_in"], 10000)
        later = {r["name"]: r for r in m.current_limits(db, t=1789800000)}
        self.assertTrue(later["5h"]["stale"])                  # 過了重置時間就當 0%
        self.assertEqual(later["5h"]["used_percent"], 0.0)
        self.assertIn("resets in 2h46m", m.render_limits(m.current_limits(db, t=1789690000)))


class CodexSync(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()

    def tearDown(self):
        self.sb.close()

    def test_sync_idempotent(self):
        env = {"CODEX_HOME": HOME}
        self.assertIn("codex    +4", self.sb.run("--sync", **env).stdout)
        os.utime(NEW)
        self.assertIn("codex    +0", self.sb.run("--sync", **env).stdout)
        d = json.loads(self.sb.run("--summary", "--month", "2026-09", "--json", "--no-sync", **env).stdout)
        codex = d["sources"][0]
        self.assertEqual(codex["totals"]["requests"], 4)
        gpt55 = [x for x in codex["models"] if x["model"] == "gpt-5.5"][0]
        # 13000 未快取 * 5 + 37000 快取 * 0.5 + 1000 寫入 * 5 + 800 輸出 * 30
        self.assertAlmostEqual(gpt55["cost_usd"], (13000 * 5 + 37000 * 0.5 + 1000 * 5 + 800 * 30) / 1e6)


if __name__ == "__main__":
    unittest.main()
