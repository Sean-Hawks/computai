import os
import unittest

from tests import helpers


class FirstRun(unittest.TestCase):
    """完全沒設定過的人第一次打開：每個空白的地方都要說下一步。"""

    def setUp(self):
        self.sb = helpers.Sandbox()

    def tearDown(self):
        self.sb.close()

    def test_no_logs_says_where_it_looked(self):
        r = self.sb.run("--summary")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no Claude Code or Codex logs found yet", r.stdout)
        self.assertIn("no-claude", r.stdout)                  # 照 CLAUDE_CONFIG_DIR 找
        self.assertNotIn("--sync", r.stdout)                  # 已經同步過了，不要再叫人跑 --sync

    def test_short_ticker_does_not_repeat(self):
        m = helpers.load()
        st = {"machines": [], "limits": [], "today_usd": 0.0}
        line = m.ticker(st, 120)
        self.assertEqual(line.count("today"), 1, line)


    def test_guess_the_plan_and_ask_once(self):
        old = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old)))
        os.environ.update(self.sb.env(CLAUDE_CONFIG_DIR=helpers.fixture("claude"), CODEX_HOME=helpers.fixture("codex"),
                                      COMPUTAI_FAKE_NOW="1789430400"))
        m = helpers.load()
        m.set_lang("en")
        db = m.open_ledger()
        self.addCleanup(db.close)
        m.sync(db, quiet=True)
        self.assertEqual(m.guess_plan(db, "codex")[0]["name"], "Pro")       # log 裡的 plan_type
        self.assertEqual(m.guess_plan(db, "claude"), ({"name": "Pro", "usd": 20.0, "capacity": 1.0}, "usage"))
        asked = []
        answers = iter(["", "PRO"])
        said = []
        n = m.ask_plans_once(db, ask=lambda q: asked.append(q) or next(answers), out=said.append)
        self.assertEqual(n, 2)
        self.assertIn("Claude Code looks like Claude Pro ($20.00/month, guessed from your usage)", asked[0])
        self.assertEqual({k: v["name"] for k, v in m.plans().items()}, {"claude": "Claude Pro", "codex": "ChatGPT Pro"})
        self.assertEqual(m.ask_plans_once(db, ask=lambda q: self.fail("asked twice")), 0)


if __name__ == "__main__":
    unittest.main()
