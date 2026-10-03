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


if __name__ == "__main__":
    unittest.main()
