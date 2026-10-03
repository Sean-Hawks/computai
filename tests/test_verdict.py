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
