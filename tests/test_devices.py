import os
import sqlite3
import tempfile
import unittest

from tests import helpers


class Migration(unittest.TestCase):
    def test_old_ledger_gets_a_device_column(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, tmp)
        path = os.path.join(tmp, "old.sqlite")
        old = sqlite3.connect(path)
        old.execute("CREATE TABLE usage (source TEXT NOT NULL, uid TEXT NOT NULL, ts INTEGER NOT NULL, "
                    "model TEXT NOT NULL DEFAULT '', project TEXT NOT NULL DEFAULT '', session TEXT NOT NULL DEFAULT '', "
                    "input INTEGER NOT NULL DEFAULT 0, cache_read INTEGER NOT NULL DEFAULT 0, "
                    "cache_write_5m INTEGER NOT NULL DEFAULT 0, cache_write_1h INTEGER NOT NULL DEFAULT 0, "
                    "output INTEGER NOT NULL DEFAULT 0, reasoning INTEGER NOT NULL DEFAULT 0, "
                    "requests INTEGER NOT NULL DEFAULT 1, subagent INTEGER NOT NULL DEFAULT 0, cost_usd REAL, "
                    "PRIMARY KEY (source, uid))")
        old.execute("INSERT INTO usage (source, uid, ts, output) VALUES ('claude', 'a', 1, 5)")
        old.commit()
        old.close()
        m = helpers.load()
        db = m.open_ledger(path)
        self.addCleanup(db.close)
        self.assertEqual(db.execute("SELECT device FROM usage").fetchone()[0], "")   # 舊資料都是這台的
        m.add_usage(db, [{"source": "codex", "uid": "b", "ts": 2, "device": "dev-2"}])
        self.assertEqual(db.execute("SELECT device FROM usage WHERE uid = 'b'").fetchone()[0], "dev-2")


if __name__ == "__main__":
    unittest.main()


class SharedFolder(unittest.TestCase):
    """兩台電腦經由共用資料夾合併：A 有 log，B 沒有；B 同步後看得到 A 的用量，而且帳本裡沒有任何內容文字。"""

    def setUp(self):
        self.a, self.b = helpers.Sandbox(), helpers.Sandbox()
        self.share = os.path.join(self.a.root, "share")
        for sb, name in ((self.a, "alpha-mac"), (self.b, "beta-pc")):
            os.makedirs(sb.config)
            with open(os.path.join(sb.config, "config.ini"), "w") as f:
                f.write("[devices]\nfolder = %s\nname = %s\n" % (self.share, name))

    def tearDown(self):
        self.a.close()
        self.b.close()

    def run_a(self, *args):
        return self.a.run(*args, CLAUDE_CONFIG_DIR=helpers.fixture("claude"), CODEX_HOME=helpers.fixture("codex"))

    def ledger(self, sb):
        db = sqlite3.connect(os.path.join(sb.data, "ledger.sqlite"))
        self.addCleanup(db.close)
        return db

    def test_merge_dedupe_privacy_and_bad_files(self):
        r = self.run_a("--sync")
        self.assertEqual(r.returncode, 0, r.stderr)
        files = sorted(os.listdir(self.share))
        self.assertEqual(len(files), 2, files)                        # <代號>.jsonl 和 <代號>.json
        a_rows = self.ledger(self.a).execute("SELECT COUNT(*) FROM usage WHERE source IN ('claude', 'codex')").fetchone()[0]
        self.assertGreater(a_rows, 0)
        r = self.b.run("--sync")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.b.run("--sync")                                          # 再同步一次不會重複計算
        db = self.ledger(self.b)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM usage WHERE device != ''").fetchone()[0], a_rows)
        self.assertEqual(db.execute("SELECT name, error FROM devices").fetchall(), [("alpha-mac", "")])
        projects = {r[0] for r in db.execute("SELECT DISTINCT project FROM usage")}
        self.assertIn("alpha", projects)                              # 只留資料夾名稱
        self.assertFalse(any("/" in p for p in projects), projects)
        # 隱私：fixture 裡的假 prompt、回應、路徑、session id 都不會出現在共用資料夾或 B 的帳本
        dump = "\n".join(db.iterdump())
        for name in files:
            with open(os.path.join(self.share, name), encoding="utf-8") as f:
                dump += f.read()
        for secret in ("FAKE PROMPT", "FAKE ASSISTANT", "/home/demo", "sess-1"):
            self.assertNotIn(secret, dump)
        # 總覽照機器分組；超過 10 分鐘沒回報就標成 stale
        r = self.b.run("--summary", "--month", "2026-09", "--no-sync")
        self.assertIn("alpha-mac", r.stdout)
        self.assertIn("beta-pc", r.stdout)
        self.assertNotIn("(stale)", r.stdout)
        late = str(int(__import__("time").time()) + 3600)
        self.assertIn("(stale)", self.b.run("--summary", "--no-sync", COMPUTAI_FAKE_NOW=late).stdout)
        r = self.b.run("--summary", "--month", "2026-09", "--by", "device", "--no-sync")
        self.assertIn("alpha-mac", r.stdout)
        # A 的檔案壞掉：B 保留上一份好的結果，記下原因
        data = [n for n in files if n.endswith(".jsonl")][0]
        with open(os.path.join(self.share, data), "a", encoding="utf-8") as f:
            f.write("{broken\n")
        self.b.run("--sync")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM usage WHERE device != ''").fetchone()[0], a_rows)
        self.assertIn("not JSON", db.execute("SELECT error FROM devices").fetchone()[0])


class ExportCommand(unittest.TestCase):
    def test_export_usage_round_trip(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        env = dict(CLAUDE_CONFIG_DIR=helpers.fixture("claude"), CODEX_HOME=helpers.fixture("codex"))
        r = sb.run("--export-usage", **env)
        self.assertEqual(r.returncode, 0, r.stderr)
        m = helpers.load()
        head, rows = m.parse_export(r.stdout)
        self.assertTrue(rows)
        self.assertNotIn("FAKE", r.stdout)
        late = max(x["ts"] for x in rows)
        r = sb.run("--export-usage", str(late), **env)
        self.assertEqual([x["ts"] for x in m.parse_export(r.stdout)[1]], [x["ts"] for x in rows if x["ts"] >= late])
        for bad in ('{"computai_export": 1, "device": "x"}', '{"computai_export": 2}',
                    r.stdout.replace('"claude"', '"local"', 1).replace('"cols"', '"cols"')):
            with self.assertRaises(ValueError):
                m.parse_export(bad)


@unittest.skipIf(os.name == "nt", "runs the remote side through sh")
class SshPull(unittest.TestCase):
    """B：用 SSH 拉。這裡的「遠端」是本機的 sh，但走的是同一套指令：檢查 python3、送檔案、匯出、合併。"""

    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.clear()
        os.environ.update(self.sb.env(CLAUDE_CONFIG_DIR=helpers.fixture("claude"), CODEX_HOME=helpers.fixture("codex")))
        self.m = helpers.load()
        self.db = self.m.open_ledger()

    def tearDown(self):
        self.db.close()
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def test_pull_copies_once_and_merges(self):
        box = {"name": "box", "host": "local", "usage": "pull"}
        calls = []
        real = self.m.run_script
        self.m.run_script = lambda host, script, timeout=25: calls.append(script[:20]) or real(host, script, timeout)
        added, err = self.m.pull_device(self.db, box)
        self.assertEqual(err, "")
        self.assertGreater(added, 0)
        remote = os.path.join(self.sb.root, ".cache", "computai")
        self.assertTrue(os.path.exists(os.path.join(remote, "computai")))
        self.assertEqual([tuple(r) for r in self.db.execute("SELECT name, via FROM devices")], [("box", "ssh")])
        n = len(calls)
        self.assertEqual(self.m.pull_device(self.db, box), (0, ""))       # 已經有了：不重送、不重複計算
        self.assertEqual(len(calls) - n, 2)                                 # 只有檢查和匯出
        self.assertNotIn("FAKE", "\n".join(self.db.iterdump()))

    def test_no_python_on_the_other_side(self):
        self.m.run_script = lambda host, script, timeout=25: "NOPY\n"
        self.assertEqual(self.m.pull_device(self.db, {"name": "box", "host": "box"}), (0, "python3 not found there"))
