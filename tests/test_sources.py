import os
import sqlite3
import unittest
from unittest import mock

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

    def test_live_wal_is_read_only_without_copying_conversation(self):
        path = os.path.join(os.environ["OPENCODE_DATA_DIR"], "opencode.db")
        writer = sqlite3.connect(path)
        self.addCleanup(writer.close)
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("UPDATE message SET data = replace(data, '\"input\":120', '\"input\":321') WHERE id = 'msg_a1'")
        writer.commit()
        self.assertTrue(os.path.exists(path + "-wal"))
        connect = sqlite3.connect
        reads = []

        def read_only_connect(*args, **kwargs):
            con = connect(*args, **kwargs)
            with self.assertRaises(sqlite3.OperationalError):
                con.execute("DELETE FROM message")
            con.rollback()
            def authorize(action, table, column, database, trigger):
                if action == sqlite3.SQLITE_READ:
                    reads.append(table)
                    return sqlite3.SQLITE_DENY if table == "part" else sqlite3.SQLITE_OK
                return sqlite3.SQLITE_OK
            con.set_authorizer(authorize)
            return con

        with mock.patch.object(self.m.shutil, "copyfile", side_effect=AssertionError("must not copy conversations")), \
                mock.patch.object(self.m.tempfile, "mkdtemp", side_effect=AssertionError("must not create database copies")), \
                mock.patch.object(sqlite3, "connect", side_effect=read_only_connect):
            rows = self.m.read_opencode_db(path)
        self.assertEqual(next(r["input"] for r in rows if r["uid"] == "msg_a1"), 321)
        self.assertNotIn("part", reads)
        self.assertNotIn("FAKE", str(rows))
        self.assertEqual(writer.execute("SELECT COUNT(*) FROM message").fetchone()[0], 4)


class Cursor(unittest.TestCase):
    def test_csv_export(self):
        m = helpers.load()
        rows = m.parse_cursor_csv(helpers.fixture("cursor", "usage-events-2026-09.csv"))
        self.assertEqual(len(rows), 3)                                       # 出錯不收費的那筆不算
        a, b, c = rows
        self.assertEqual((a["model"], a["input"], a["cache_write_5m"], a["cache_read"], a["output"], a["cost_usd"]),
                         ("claude-4.6-sonnet-medium-thinking", 300, 1200, 8000, 450, None))
        self.assertEqual((b["cost_usd"], c["input"]), (0.04, 1500))              # 有千分位逗號也讀得懂
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        r = sb.run("--import-cursor", helpers.fixture("cursor", "usage-events-2026-09.csv"))
        self.assertIn("3 Cursor rows read, 3 new", r.stdout)
        r = sb.run("--import-cursor", helpers.fixture("cursor", "usage-events-2026-09.csv"))
        self.assertIn("0 new", r.stdout)                                     # 重複匯入不重複計算

    def test_not_a_cursor_file(self):
        import tempfile
        m = helpers.load()
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("a,b\n1,2\n")
        self.addCleanup(os.remove, f.name)
        self.assertEqual(m.parse_cursor_csv(f.name), [])


if __name__ == "__main__":
    unittest.main()
