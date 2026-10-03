import json
import os
import subprocess
import sys
import unittest

from tests import helpers

NOW = 1790000000  # 2026-09-21 14:13:20 UTC


class Line(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.env = dict(COMPUTAI_FAKE_NOW=NOW, CLAUDE_CONFIG_DIR=helpers.fixture("claude"),
                        CODEX_HOME=helpers.fixture("codex"))

    def tearDown(self):
        self.sb.close()

    def statusline(self, name):
        with open(helpers.fixture("statusline", name)) as f:
            return subprocess.run([sys.executable, helpers.SCRIPT, "--statusline"], stdin=f,
                                  env=self.sb.env(**self.env), capture_output=True, text=True,
                                  encoding="utf-8", timeout=60)

    def test_line_without_claude_limits(self):
        r = self.sb.run("--line", **self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        # 5 小時視窗在 NOW 之前就重置了（0%），每週視窗最後一筆是 10%
        self.assertEqual(r.stdout.strip(), "Codex 90% left｜today $0.0")

    def test_statusline_records_claude_limits(self):
        r = self.statusline("max.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("Claude 58% left｜"), r.stdout)
        # 之後單純的 --line 也看得到 Claude 的額度
        d = json.loads(self.sb.run("--line", "--json", **self.env).stdout)
        claude = [p for p in d["limits"] if p["source"] == "claude"][0]
        self.assertEqual((claude["used_percent"], claude["window"], claude["resets_in"]), (42.4, "5h", 3600))

    def test_statusline_without_limits(self):
        r = self.statusline("no-limits.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("Claude", r.stdout)

    def test_high_usage_shows_countdown(self):
        m = helpers.load()
        info = {"limits": [{"label": "Codex", "used_percent": 97.0, "resets_in": 7200}], "today_usd": 123.4}
        self.assertEqual(m.render_line(info, " | "), "Codex 3% left (2h00m) | today $123")


if __name__ == "__main__":
    unittest.main()
