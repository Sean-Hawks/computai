import os
import sqlite3
import unittest
from unittest import mock

from tests import helpers


class UpdaterCache(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.addCleanup(self.sb.close)
        self.env = mock.patch.dict(os.environ, self.sb.env())
        self.env.start()
        self.addCleanup(self.env.stop)
        self.m = helpers.load()
        self.db = self.m.open_ledger()
        self.addCleanup(self.db.close)
        self.writer = sqlite3.connect(self.m.ledger_path())
        self.addCleanup(self.writer.close)

    def add(self, db, uid="new"):
        db.execute("INSERT INTO usage (source, uid, ts) VALUES ('codex', ?, 1)", (uid,))
        db.commit()

    def run_updater(self, loops=4, tick=None, build=None, notify=None, callback=None):
        clock = [1000.0]
        cycles = [0]
        updater = self.m.Updater(notify=notify is not None)

        class Stop:
            def is_set(self):
                return cycles[0] >= loops

            def wait(self, timeout):
                cycles[0] += 1
                clock[0] += 5

        class Connection:
            def __getattr__(_, key):
                return getattr(self.db, key)

            def close(_):
                pass

        updater.stop = Stop()
        delivered = []
        builds = []

        def state(db):
            value = {"count": db.execute("SELECT COUNT(*) FROM usage").fetchone()[0]}
            builds.append(cycles[0])
            if build:
                build(db, cycles[0])
            return value

        def on_state(st):
            if callback:
                callback(st, cycles[0])
            delivered.append(st["count"])

        with mock.patch.object(self.m, "open_ledger", return_value=Connection()), \
                mock.patch.object(updater, "tick", side_effect=lambda db: tick(db, cycles[0]) if tick else None), \
                mock.patch.object(self.m, "insights", return_value=[]), \
                mock.patch.object(self.m, "dashboard_state", side_effect=state), \
                mock.patch.object(self.m, "notify_tick", side_effect=notify), \
                mock.patch.object(self.m, "warn"), \
                mock.patch.object(self.m.time, "monotonic", side_effect=lambda: clock[0]):
            updater.run(on_state, 5)
        return delivered, builds

    def test_unchanged_ledger_refreshes_after_a_minute(self):
        self.assertEqual(self.run_updater(loops=14), ([0, 0], [0, 12]))

    def test_own_usage_change_refreshes_next_cycle(self):
        got, builds = self.run_updater(tick=lambda db, cycle: self.add(db) if cycle == 1 else None)
        self.assertEqual((got, builds), ([0, 1], [0, 1]))

    def test_external_usage_change_refreshes_next_cycle(self):
        got, builds = self.run_updater(tick=lambda db, cycle: self.add(self.writer) if cycle == 1 else None)
        self.assertEqual((got, builds), ([0, 1], [0, 1]))

    def test_external_commit_during_build_is_not_marked_as_displayed(self):
        got, builds = self.run_updater(build=lambda db, cycle: self.add(self.writer) if cycle == 0 else None)
        self.assertEqual((got, builds), ([0, 1], [0, 1]))

    def test_notification_metadata_does_not_force_a_rebuild(self):
        def notify(db, state):
            db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('notify_state', '{}')")
            db.commit()
        self.assertEqual(self.run_updater(notify=notify), ([0], [0]))

    def test_callback_failure_retries_next_cycle(self):
        def callback(state, cycle):
            if cycle == 0:
                raise RuntimeError("synthetic delivery failure")
        self.assertEqual(self.run_updater(callback=callback), ([0], [0, 1]))

    def test_build_failure_retries_next_cycle(self):
        def build(db, cycle):
            if cycle == 0:
                raise RuntimeError("synthetic build failure")
        self.assertEqual(self.run_updater(build=build), ([0], [0, 1]))
