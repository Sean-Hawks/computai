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

    def test_no_limits_says_how_to_connect(self):
        r = self.sb.run("--once", COLUMNS="100")
        self.assertIn("install and log in to the claude or codex CLI", " ".join(r.stdout.split()))

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


    def test_beta_versions_sort_in_release_order(self):
        m = helpers.load()
        versions = ["0.1.0-alpha.1", "0.1.0-beta.1", "0.1.0-beta.2-dev", "0.1.0-beta.2",
                    "0.1.0-beta.10", "0.1.0-rc.1", "0.1.0", "0.1.1-beta.1"]
        self.assertEqual(sorted(reversed(versions), key=m.version_tuple), versions)

    def test_update_check_once_a_day(self):
        old = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old)))
        os.environ.update(self.sb.env())
        os.environ.pop("COMPUTAI_NO_UPDATE_CHECK", None)
        m = helpers.load()
        db = m.open_ledger()
        self.addCleanup(db.close)
        calls = []
        fetch = lambda: calls.append(1) or "9.0.0"
        self.assertEqual(m.check_update(db, fetch=fetch, t=1000), "9.0.0")
        self.assertEqual(m.check_update(db, fetch=fetch, t=1000 + 3600), "9.0.0")   # 一天內不再連網
        self.assertEqual(len(calls), 1)
        m.check_update(db, fetch=lambda: calls.append(1) or m.__version__, t=1000 + 86400)
        self.assertEqual((len(calls), m.newer_version(db)), (2, None))              # 已經是最新
        self.assertTrue(m.version_tuple("0.2.0") > m.version_tuple("0.2.0b1") > m.version_tuple("0.1.0"))
        m.write_config([("general", "update_check", "no")])
        self.assertIsNone(m.check_update(db, fetch=lambda: self.fail("should not fetch"), t=10 ** 9))
        os.environ["COMPUTAI_NO_UPDATE_CHECK"] = "1"
        self.assertFalse(m.update_check_on())


if __name__ == "__main__":
    unittest.main()
