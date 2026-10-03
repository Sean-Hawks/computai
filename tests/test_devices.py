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
