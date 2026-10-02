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
