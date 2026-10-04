"""Remote session identity using synthetic usage; never read personal logs."""
import json
import os
import unittest
from unittest import mock

from tests import helpers


class RemoteSessions(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.env = mock.patch.dict(os.environ, self.sb.env())
        self.env.start()
        self.addCleanup(self.sb.close)
        self.addCleanup(self.env.stop)
        self.m = helpers.load()
        self.a = self.m.open_ledger(":memory:")
        self.b = self.m.open_ledger(":memory:")
        self.addCleanup(self.a.close)
        self.addCleanup(self.b.close)
        with open(helpers.fixture("devices", "legacy.jsonl"), encoding="utf-8") as f:
            self.legacy = f.read()
        self.head, rows = self.m.parse_export(self.legacy)
        self.rows = [dict(r, device="", session="PRIVATE-SESSION-" + r["uid"].split("-")[1][0]) for r in rows]
        self.m.add_usage(self.a, self.rows)
        self.a.execute("INSERT INTO meta VALUES ('device_id', 'fixture-box')")

    def export(self):
        return self.m.export_usage(self.a, t=self.head["written"])[0]

    def test_stable_scoped_hashes_and_legacy_compatibility(self):
        text = self.export()
        head, rows = self.m.parse_export(text)
        self.assertTrue(head["sessions"])
        self.assertEqual(len({r["session"] for r in rows}), 2)
        self.assertEqual(rows[0]["session"], rows[2]["session"])
        self.assertTrue(all(len(r["session"]) == 16 for r in rows))
        self.assertNotIn("PRIVATE-SESSION", text)
        self.assertEqual(text, self.export())
        # A beta.1 reader selects just its original whitelist columns.
        lines = [json.loads(line) for line in text.splitlines()]
        old_cols = self.m.EXPORT_COLS[:-1]
        old_rows = [dict(zip(old_cols, (arr[lines[0]["cols"].index(c)] for c in old_cols))) for arr in lines[1:]]
        self.assertEqual({r["uid"] for r in old_rows}, {r["uid"] for r in rows})
        old_head, old_rows = self.m.parse_export(self.legacy)
        self.assertFalse(old_head["sessions"])
        self.assertTrue(all(r["session"] == "" for r in old_rows))
        self.a.execute("UPDATE meta SET value = 'another-box' WHERE key = 'device_id'")
        other = self.m.parse_export(self.export())[1]
        self.assertTrue(all(x["session"] != y["session"] for x, y in zip(rows, other)))

    def test_reject_invalid_hash_without_partial_import(self):
        lines = [json.loads(line) for line in self.export().splitlines()]
        idx = lines[0]["cols"].index("session")
        for bad in (None, True, 123, [], "raw-session", "a" * 15, "A" * 16, "a" * 17, "f" * 16 + "\n"):
            with self.subTest(bad=bad):
                lines[-1][idx] = bad
                with self.assertRaisesRegex(ValueError, "bad session hash"):
                    self.m.parse_export("\n".join(json.dumps(x) for x in lines))

    def test_backfill_without_rolling_back_tokens_or_replacing_local_sessions(self):
        old_head, old_rows = self.m.parse_export(self.legacy)
        self.assertEqual(self.m.merge_export(self.b, old_head, old_rows, "folder"), 4)
        self.b.execute("UPDATE usage SET output = 100, requests = 2 WHERE uid = 'demo-a1'")
        head, rows = self.m.parse_export(self.export())
        self.assertEqual(self.m.merge_export(self.b, head, rows, "folder"), 4)
        self.assertEqual(self.m.merge_export(self.b, head, rows, "ssh"), 0)
        self.assertEqual(self.m.merge_export(self.b, old_head, old_rows, "folder"), 0)
        self.assertEqual(self.b.execute("SELECT COUNT(*), COUNT(DISTINCT session) FROM usage").fetchone()[:], (4, 2))
        self.assertEqual(self.b.execute("SELECT output, requests FROM usage WHERE uid = 'demo-a1'").fetchone()[:], (100, 2))
        self.assertNotIn("PRIVATE-SESSION", "\n".join(self.b.iterdump()))
        # The same record can also exist in local logs or another device's export.
        self.m.add_usage(self.a, rows)
        self.assertTrue(all(r[0].startswith("PRIVATE-SESSION") for r in self.a.execute("SELECT session FROM usage")))
        self.b.execute("UPDATE usage SET session = '', device = 'different-box'")
        self.assertEqual(self.m.merge_export(self.b, head, rows, "ssh"), 0)
        self.assertTrue(all(r[0] == "" for r in self.b.execute("SELECT session FROM usage")))

    def test_imported_sessions_restore_timeline_and_card_statistics(self):
        head, rows = self.m.parse_export(self.export())
        self.m.merge_export(self.b, head, rows, "folder")
        start = min(r["ts"] for r in rows) - 60
        end = max(r["ts"] for r in rows) + 60
        tl = self.m.timeline_data(self.b, start, end, prices={})
        self.assertEqual(len(tl["rows"]), 2)
        self.assertEqual(tl["stats"]["peak"], 2)
        self.assertEqual(tl["stats"]["longest"]["seconds"], 240)
        self.assertEqual(tl["stats"]["agent_seconds"], 480)
        card = self.m.card_ops(self.b, start, end)
        self.assertEqual((card["peak_parallel"], card["longest_run"], card["agent_hours"]), (2, 240, 0.1))

    def test_unknown_session_stays_empty(self):
        self.a.execute("UPDATE usage SET session = ''")
        rows = self.m.parse_export(self.export())[1]
        self.assertTrue(all(r["session"] == "" for r in rows))
