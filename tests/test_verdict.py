import unittest

from tests import helpers


def lim(source, name, used, resets_in=3600):
    return {"source": source, "name": name, "used_percent": used, "resets_in": resets_in, "window_minutes": 300}


class Verdict(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.m.set_lang("en")

    def test_all_clear(self):
        v = self.m.verdict({"limits": [lim("claude", "5h", 42)], "alerts": [], "forecast": {}})
        self.assertEqual((v["level"], v["word"], v["items"]), ("ok", "ALL CLEAR", []))

    def test_worst_first(self):
        st = {"limits": [lim("claude", "5h", 85), lim("codex", "week", 100, 18480)],
              "alerts": [{"kind": "idle_model", "machine": "mac", "message": "..."}],
              "forecast": {"over_budget": False}}
        v = self.m.verdict(st)
        self.assertEqual(v["level"], "fail")
        self.assertEqual(v["items"][0], ("fail", "Codex weekly limit is used up - resets in 5h08m"))
        self.assertEqual([x[0] for x in v["items"]], ["fail", "warn", "warn"])
        self.assertIn("Claude Code 5-hour limit is 85% used", v["items"][1][1])

    def test_unreachable_and_budget(self):
        st = {"limits": [], "alerts": [{"kind": "machine_unreachable", "machine": "wsl", "message": "timeout"}],
              "forecast": {"over_budget": True, "projected_usd": 320, "budget_usd": 300}}
        v = self.m.verdict(st)
        self.assertEqual([x[1] for x in v["items"]],
                         ["wsl cannot be reached", "this month is heading for $320.00, over the $300.00 budget"])

    def test_zh(self):
        self.m.set_lang("zh")
        v = self.m.verdict({"limits": [lim("codex", "week", 100, 18480)], "alerts": [], "forecast": {}})
        self.assertEqual(v["word"], "警告")
        self.assertEqual(v["items"][0][1], "Codex 每週額度用完了，5h08m 後重置")


if __name__ == "__main__":
    unittest.main()


class Pace(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")

    def pace(self, rows, t):
        self.m.add_limits(self.db, [dict(source="codex", name="5h", ts=ts, used_percent=u, window_minutes=300,
                                         resets_at=10000 + 18000) for ts, u in rows])
        return [r for r in self.m.current_limits(self.db, t) if r["name"] == "5h"][0]

    def test_average_pace_runs_out_before_reset(self):
        # 週期 10000-28000；過了一半（t=19000）已經用 60%：照這速度 15000 秒後……其實 6000 秒就用完
        r = self.pace([(19000, 60.0)], 19000)
        self.assertEqual(r["elapsed_pct"], 50.0)
        self.assertEqual(r["eta_full"], 6000)
        self.assertEqual(r["projected_pct"], 120)

    def test_recent_rate_wins(self):
        # 最近一小時從 30% 到 31%：很慢，重置時只會到 ~34%
        r = self.pace([(15400, 30.0), (19000, 31.0)], 19000)
        self.assertIsNone(r["eta_full"])
        self.assertEqual(r["projected_pct"], 34)

    def test_used_up(self):
        r = self.pace([(19000, 100.0)], 19000)
        self.assertEqual(r["eta_full"], 0)


class StaleLimits(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.m.set_lang("en")

    def test_old_used_up_reading_is_a_hint_not_a_fact(self):
        r = dict(lim("codex", "week", 100, 5000), age=26 * 3600)
        v = self.m.verdict({"limits": [r], "alerts": [], "forecast": {}})
        self.assertEqual(v["level"], "warn")
        self.assertIn("was used up when last seen 1d2h ago", v["items"][0][1])
        self.assertIn("computai --limit-reset", v["items"][0][1])
        self.m.set_style(color=False)
        self.assertIn("seen 1d2h ago", self.m.limit_note(r))
        fresh = dict(lim("codex", "week", 100, 5000), age=60)
        self.assertEqual(self.m.verdict({"limits": [fresh], "alerts": [], "forecast": {}})["level"], "fail")

    def test_limit_reset_until_the_next_real_reading(self):
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        self.m.add_limits(db, [dict(source="codex", name="week", ts=1000, used_percent=100.0, window_minutes=10080,
                                    resets_at=900000)])
        rows = self.m.limit_reset_rows(db, "codex", t=2000)
        self.assertEqual([(r["name"], r["used_percent"], r["resets_at"]) for r in rows], [("week", 0.0, None)])
        self.m.add_limits(db, rows)
        self.assertEqual(self.m.current_limits(db, 2100)[0]["used_percent"], 0.0)
        self.m.add_limits(db, [dict(source="codex", name="week", ts=3000, used_percent=12.0, window_minutes=10080,
                                    resets_at=600000)])
        self.assertEqual(self.m.current_limits(db, 3100)[0]["used_percent"], 12.0)   # 真的數字回來就取代
