import os
import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

from tests import helpers


LEGACY = """CREATE TABLE limits (
source TEXT NOT NULL, name TEXT NOT NULL, ts INTEGER NOT NULL,
used_percent REAL, window_minutes INTEGER, resets_at INTEGER,
plan TEXT NOT NULL DEFAULT '', PRIMARY KEY (source, name, ts));"""


class LimitsMigration(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.addCleanup(self.sb.close)
        self.path = os.path.join(self.sb.root, "old.sqlite")
        self.m = helpers.load()
        self.rows = [("codex", "week", i, i % 100, 10080, 1791593542, "pro") for i in range(500)]
        db = sqlite3.connect(self.path)
        db.executescript(LEGACY)
        db.executemany("INSERT INTO limits VALUES (?,?,?,?,?,?,?)", self.rows)
        db.commit()
        db.close()

    def test_parallel_open_preserves_all_legacy_values_and_the_index(self):
        ready = threading.Barrier(2)

        def open_and_read():
            ready.wait(timeout=10)
            db = self.m.open_ledger(self.path)
            try:
                got = [tuple(r) for r in db.execute(
                    "SELECT source, name, ts, used_percent, window_minutes, resets_at, plan FROM limits ORDER BY ts")]
                self.assertEqual(got, self.rows)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM limits WHERE account != ''").fetchone()[0], 0)
                self.assertIn("limits_source_ts", [r[1] for r in db.execute("PRAGMA index_list(limits)")])
                return len(got)
            finally:
                db.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: open_and_read(), range(2)))
        self.assertEqual(results, [500, 500])
        db = self.m.open_ledger(self.path)
        try:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM limits").fetchone()[0], 500)
        finally:
            db.close()

    def test_failed_migration_rolls_back_to_the_complete_legacy_table(self):
        db = sqlite3.connect(self.path)
        self.addCleanup(db.close)

        def authorize(action, name, *_):
            return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_DROP_TABLE and name == "limits_old" else sqlite3.SQLITE_OK
        db.set_authorizer(authorize)
        with self.assertRaises(sqlite3.DatabaseError):
            self.m.migrate_limits_account(db)
        db.set_authorizer(lambda *_: sqlite3.SQLITE_OK)
        self.assertNotIn("account", [r[1] for r in db.execute("PRAGMA table_info(limits)")])
        self.assertEqual(db.execute("SELECT * FROM limits ORDER BY ts").fetchall(), self.rows)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='limits_old'").fetchone()[0], 0)
        self.m.migrate_limits_account(db)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM limits WHERE account='' ").fetchone()[0], 500)
