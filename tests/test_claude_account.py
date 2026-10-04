import json
import os
import stat
import tempfile
import unittest

from tests import helpers

# 假的 claude：照真的 `claude -p /usage --output-format stream-json` 的形狀輸出，
# 文字報告裡放一段不該被存下來的內容。
FAKE = r"""#!/usr/bin/env python3
import json, os, sys
assert sys.argv[1:3] == ["-p", "/usage"], sys.argv
print(json.dumps({"type": "system", "subtype": "init", "cwd": "/tmp"}))
print(json.dumps({"type": "assistant", "local_command_source": "SECRET-REPORT top skills /private-thing",
                  "usage_report": {"session": {"total_cost_usd": 0}, "rate_limits": {"limits": [
    {"kind": "session", "group": "session", "percent": 70 if os.environ.get("CLAUDE_CONFIG_DIR", "").endswith("-nycu") else 12, "resets_at": "2026-10-03T20:30:00.220018+00:00"},
    {"kind": "weekly_all", "group": "weekly", "percent": 26, "resets_at": "2026-10-09T10:00:00+00:00"},
    {"kind": "weekly_scoped", "percent": 0, "resets_at": "2026-10-09T10:00:00+00:00",
     "scope": {"model": {"display_name": "Fable"}}},
    {"kind": "weekly_scoped", "percent": 40, "resets_at": "2026-10-09T10:00:00+00:00",
     "scope": {"model": {"display_name": "Opus"}}}]}}}))
print(json.dumps({"type": "result", "subtype": "success", "num_turns": 0, "total_cost_usd": 0}))
"""


class ClaudeAccount(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        path = os.path.join(self.tmp, "claude")
        with open(path, "w") as f:
            f.write(FAKE)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        self.old = dict(os.environ)
        os.environ["PATH"] = self.tmp + os.pathsep + os.environ["PATH"]
        os.environ.pop("COMPUTAI_FIXTURES", None)
        self.m = helpers.load()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        import shutil
        shutil.rmtree(self.tmp)

    @unittest.skipIf(os.name == "nt", "fake claude is a POSIX script")
    def test_reads_account_limits_through_the_claude_cli(self):
        rows = self.m.claude_account_limits(t=1790000000)
        self.assertEqual([(r["name"], r["used_percent"], r["window_minutes"], r["resets_at"]) for r in rows],
                         [("5h", 12.0, 300, 1791059400), ("week", 26.0, 10080, 1791540000),
                          ("week:Opus", 40.0, 10080, 1791540000)])   # 用了 0% 的單一模型額度不記
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        self.assertEqual(self.m.claude_account_poll(db, t=1790000000), 3)
        self.assertEqual(self.m.claude_account_poll(db, t=1790000600), 0)       # 沒變就不寫
        self.assertNotIn("SECRET-REPORT", "\n".join(db.iterdump()))             # 文字報告不留
        self.assertEqual(self.m.limit_label("week:Opus"), "weekly limit (Opus)")

    @unittest.skipIf(os.name == "nt", "fake claude is a POSIX script")
    def test_polls_every_listed_account(self):
        homes = [os.path.join(self.tmp, d) for d in (".claude", ".claude-nycu")]
        for h in homes:
            os.mkdir(h)
        os.environ["CLAUDE_CONFIG_DIR"] = ",".join(homes)
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        self.m.claude_account_poll(db, t=1790000000)
        got = {(r["account"], r["used_percent"]) for r in self.m.current_limits(db, t=1790000000) if r["name"] == "5h"}
        self.assertEqual(got, {("", 12.0), ("nycu", 70.0)})

    def test_no_claude_cli(self):
        os.environ["PATH"] = "/nonexistent"
        self.assertEqual(self.m.claude_account_limits(), [])


if __name__ == "__main__":
    unittest.main()
