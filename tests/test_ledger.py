import os
import unittest

from tests import helpers


class Ledger(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)

    def row(self, uid, **kw):
        r = dict(source="test", uid=uid, ts=1790000000, model="m", input=10, output=5)
        r.update(kw)
        return r

    def test_import_is_idempotent(self):
        rows = [self.row("a"), self.row("b")]
        self.assertEqual(self.m.add_usage(self.db, rows), 2)
        self.assertEqual(self.m.add_usage(self.db, rows), 0)
        self.assertEqual(self.m.add_usage(self.db, rows + [self.row("c")]), 1)
        n = self.db.execute("SELECT COUNT(*), SUM(input) FROM usage").fetchone()
        self.assertEqual(tuple(n), (3, 30))

    def test_partial_record_grows(self):
        self.m.add_usage(self.db, [self.row("a", output=8)])
        self.assertEqual(self.m.add_usage(self.db, [self.row("a", output=377)]), 1)
        self.assertEqual(self.m.add_usage(self.db, [self.row("a", output=8)]), 0)  # 不會縮回去
        self.assertEqual(self.db.execute("SELECT output FROM usage").fetchone()[0], 377)

    def test_same_uid_different_source(self):
        self.m.add_usage(self.db, [self.row("a"), self.row("a", source="other")])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM usage").fetchone()[0], 2)

    def test_limits_keep_accounts_apart(self):
        lim = [dict(source="codex", account=a, name="week", ts=1, used_percent=u, window_minutes=10080, resets_at=None)
               for a, u in (("", 10.0), ("nycu", 80.0))]
        self.assertEqual(self.m.add_limits(self.db, lim), 2)                     # 同一秒、同一個視窗，兩個帳號都留
        self.assertEqual(self.m.add_limits(self.db, lim, only_changes=True), 0)
        got = {(r["account"], r["used_percent"]) for r in self.m.current_limits(self.db, t=2)}
        self.assertEqual(got, {("", 10.0), ("nycu", 80.0)})

    def test_account_name_comes_from_the_config_folder(self):
        n = self.m.account_name
        self.assertEqual([n("claude", "/u/.claude"), n("claude", "/u/.config/claude"), n("codex", "/u/.codex/"),
                          n("claude", "/u/.claude-nycu"), n("codex", "/u/.codex-cs14"), n("codex", "/w/work")],
                         ["", "", "", "nycu", "cs14", "work"])

    def test_other_accounts_are_named_where_limits_show(self):
        lim = [dict(source="claude", account=a, name="5h", ts=1, used_percent=u, window_minutes=300, resets_at=None)
               for a, u in (("", 10.0), ("nycu", 80.0))]
        self.m.add_limits(self.db, lim)
        rows = self.m.current_limits(self.db, t=2)
        self.assertEqual(sorted(self.m.limit_source(r) for r in rows), ["Claude Code", "Claude Code nycu"])
        labels = [self.m.limit_metric_labels(r) for r in rows]
        self.assertIn({"source": "claude", "window": "5h"}, labels)              # 預設帳號的指標不變
        self.assertIn({"source": "claude", "account": "nycu", "window": "5h"}, labels)
        old = os.environ.get("CLAUDE_CONFIG_DIR")
        self.addCleanup(lambda: os.environ.pop("CLAUDE_CONFIG_DIR") if old is None
                        else os.environ.update(CLAUDE_CONFIG_DIR=old))
        os.environ["CLAUDE_CONFIG_DIR"] = "/u/.claude-nycu"                     # statusline 在 nycu 底下跑
        self.assertEqual([p["used_percent"] for p in self.m.line_parts(self.db)["limits"]], [80.0])

    def test_folders_without_limits_are_skipped_after_a_few_tries(self):
        asked = []

        def ask(home):
            asked.append(home)
            return [{"name": "5h"}] if home == "real" else []
        for _ in range(5):
            self.m.poll_homes(["real", "proxy"], ask)
        self.assertEqual(asked.count("real"), 5)
        self.assertEqual(asked.count("proxy"), self.m.NO_LIMITS_TRIES)          # 之後一小時內不再問

    def test_old_limits_table_moves_to_default_account(self):
        import sqlite3
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "old.sqlite")
        old = sqlite3.connect(path)
        old.execute("CREATE TABLE limits (source TEXT NOT NULL, name TEXT NOT NULL, ts INTEGER NOT NULL, "
                    "used_percent REAL, window_minutes INTEGER, resets_at INTEGER, plan TEXT NOT NULL DEFAULT '', "
                    "PRIMARY KEY (source, name, ts))")
        old.execute("INSERT INTO limits VALUES ('codex', 'week', 1, 39.0, 10080, NULL, 'pro')")
        old.commit()
        old.close()
        db = self.m.open_ledger(path)
        self.addCleanup(db.close)
        self.assertEqual([tuple(r) for r in db.execute("SELECT source, account, name, used_percent, plan FROM limits")],
                         [("codex", "", "week", 39.0, "pro")])
        self.assertEqual(self.m.open_ledger(path).execute("SELECT COUNT(*) FROM limits").fetchone()[0], 1)   # 只搬一次

    def test_limits_idempotent(self):
        lim = [dict(source="codex", name="primary", ts=1, used_percent=40.0, window_minutes=300,
                    resets_at=100, plan="pro")]
        self.assertEqual(self.m.add_limits(self.db, lim), 1)
        self.assertEqual(self.m.add_limits(self.db, lim), 0)

    def test_limits_only_changes(self):
        lim = lambda ts, pct: dict(source="claude", name="5h", ts=ts, used_percent=pct, resets_at=99)
        self.assertEqual(self.m.add_limits(self.db, [lim(1, 40.0)], only_changes=True), 1)
        self.assertEqual(self.m.add_limits(self.db, [lim(2, 40.0)], only_changes=True), 0)
        self.assertEqual(self.m.add_limits(self.db, [lim(3, 41.0)], only_changes=True), 1)

    def test_file_tracking(self):
        sb = helpers.Sandbox()
        try:
            os.makedirs(sb.root, exist_ok=True)
            p = os.path.join(sb.root, "x.jsonl")
            with open(p, "w") as f:
                f.write("a\n")
            sig = self.m.file_changed(self.db, p)
            self.assertIsNotNone(sig)
            with open(p, "a") as f:          # 讀檔途中被追加
                f.write("late\n")
            self.m.mark_file(self.db, p, sig)
            self.assertIsNotNone(self.m.file_changed(self.db, p))   # 下次還會再讀
            self.m.mark_file(self.db, p)
            self.assertIsNone(self.m.file_changed(self.db, p))
            with open(p, "a") as f:
                f.write("b\n")
            self.assertIsNotNone(self.m.file_changed(self.db, p))
        finally:
            sb.close()


if __name__ == "__main__":
    unittest.main()
