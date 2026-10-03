import os
import sqlite3
import unittest

from tests import helpers


class Gemini(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(self.sb.env(GEMINI_CLI_HOME=helpers.fixture("gemini")))
        self.m = helpers.load()
        self.db = self.m.open_ledger()

    def tearDown(self):
        self.db.close()
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def test_usage_only_dedupe_and_subagent(self):
        self.assertEqual(self.m.sync_gemini(self.db), 3)
        rows = {r["uid"].split(":")[1]: dict(r) for r in self.db.execute("SELECT * FROM usage WHERE source = 'gemini'")}
        g1 = rows["g1"]                                                       # 寫了兩次，取最後那筆
        self.assertEqual((g1["input"], g1["cache_read"], g1["output"], g1["reasoning"]), (605, 400, 70, 20))
        self.assertEqual((g1["model"], g1["project"]), ("gemini-3-flash-preview", "/home/demo/gamma"))
        self.assertEqual((rows["g2"]["input"], rows["g2"]["cache_read"]), (500, 1500))
        s1 = rows["s1"]
        self.assertEqual((s1["subagent"], s1["session"]), (1, "aaaa1111-0000-4000-8000-000000000001"))
        self.assertEqual(self.m.sync_gemini(self.db), 0)                      # 再同步一次不會重複
        dump = "\n".join(self.db.iterdump())
        for secret in ("FAKE PROMPT", "FAKE ASSISTANT", "FAKE THOUGHT", "FAKE SECRET", "FAKE ERROR", "FAKE SUBAGENT"):
            self.assertNotIn(secret, dump)


class OpenCode(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        home = os.path.join(self.sb.root, "opencode")
        import shutil
        shutil.copytree(helpers.fixture("opencode", "storage"), os.path.join(home, "storage"))
        con = sqlite3.connect(os.path.join(home, "opencode.db"))
        with open(helpers.fixture("opencode", "opencode.sql"), encoding="utf-8") as f:
            con.executescript(f.read())
        con.close()
        self.old = dict(os.environ)
        os.environ.update(self.sb.env(OPENCODE_DATA_DIR=home))
        self.m = helpers.load()
        self.db = self.m.open_ledger()

    def tearDown(self):
        self.db.close()
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def test_usage_only_subagents_and_legacy_files(self):
        self.assertEqual(self.m.sync_opencode(self.db), 3)                   # 兩則 sqlite 裡的，一則舊版 JSON；錯誤訊息沒有 token 不算
        rows = {r["uid"]: dict(r) for r in self.db.execute("SELECT * FROM usage WHERE source = 'opencode'")}
        a1 = rows["msg_a1"]
        self.assertEqual((a1["input"], a1["cache_read"], a1["cache_write_5m"], a1["output"], a1["reasoning"]),
                         (120, 5000, 800, 340, 40))
        self.assertEqual((a1["model"], a1["project"], a1["cost_usd"], a1["ts"]), ("claude-sonnet-5", "/home/demo/delta", 0.0123, 1789000002))
        self.assertEqual((rows["msg_a2"]["subagent"], rows["msg_a2"]["session"]), (1, "ses_main"))
        self.assertIsNone(rows["msg_a2"]["cost_usd"])                         # 0 = OpenCode 不知道，改用價目表
        self.assertEqual(rows["msg_old1"]["output"], 10)
        self.assertEqual(self.m.sync_opencode(self.db), 0)                   # 沒變就不重讀
        dump = "\n".join(self.db.iterdump())
        for secret in ("FAKE", "fake-slug"):
            self.assertNotIn(secret, dump)


if __name__ == "__main__":
    unittest.main()
