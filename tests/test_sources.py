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


if __name__ == "__main__":
    unittest.main()
