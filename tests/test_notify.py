import unittest

from tests import helpers


def lim(source, name, used, resets_at=50000, stale=False):
    return {"source": source, "name": name, "used_percent": used, "resets_at": resets_at,
            "resets_in": 3600, "window_minutes": 300, "stale": stale, "eta_full": None}


class Notify(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.m.set_lang("en")
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)

    def step(self, limits, alerts=()):
        return self.m.notify_events(self.db, {"limits": limits, "alerts": list(alerts), "forecast": {}})

    def test_first_run_is_silent_then_transitions_once(self):
        self.assertEqual(self.step([lim("codex", "week", 85)]), [])           # 第一次只記下現況
        self.assertEqual(self.step([lim("codex", "week", 86)]), [])           # 還是 high，不重講
        ev = self.step([lim("codex", "week", 100), lim("claude", "5h", 40)])
        self.assertEqual(ev, [("fail", "Codex weekly limit is used up - resets in 1h00m. Claude Code still has 60% left.")])
        self.assertEqual(self.step([lim("codex", "week", 100), lim("claude", "5h", 40)]), [])
        ev = self.step([lim("codex", "week", 0.0, stale=True), lim("claude", "5h", 40)])
        self.assertEqual(ev, [("ok", "Codex weekly limit has reset - you can use it again")])

    def test_crossing_80(self):
        self.step([lim("claude", "5h", 50)])
        self.assertEqual(self.step([lim("claude", "5h", 82)]), [("warn", "Claude Code 5-hour limit is 82% used.")])

    def test_new_alert_once(self):
        a = {"kind": "machine_unreachable", "machine": "wsl", "message": "wsl: timeout"}
        self.step([])
        self.assertEqual(self.step([], [a]), [("fail", "wsl: timeout")])
        self.assertEqual(self.step([], [a]), [])

    def test_deliver_uses_desktop_and_chat(self):
        sent = []
        self.m.notify_desktop = lambda title, text: sent.append(("desktop", text))
        self.m.send_report = lambda text: sent.append(("chat", text)) or []
        n = self.m.deliver([("ok", "a"), ("warn", "b")], {"desktop": True, "chat": True})
        self.assertEqual(n, 2)
        self.assertEqual(sent, [("desktop", "a"), ("desktop", "b"), ("chat", "✓ a\n⚠ b")])


if __name__ == "__main__":
    unittest.main()


class WatchService(unittest.TestCase):
    @unittest.skipUnless(__import__("sys").platform == "darwin", "launchd")
    def test_launchd_plist(self):
        import os, subprocess, tempfile
        m = helpers.load()
        calls = []
        m.run_cmd = lambda argv, **k: calls.append(argv) or ""
        with tempfile.TemporaryDirectory() as home:
            old = dict(os.environ)
            os.environ.update(HOME=home, COMPUTAI_DATA_DIR=os.path.join(home, "data"))
            try:
                what, path = m.watch_service(True)
                self.assertEqual(what, "installed")
                text = open(path).read()
                self.assertIn("<string>--watch</string>", text)
                self.assertEqual(subprocess.run(["plutil", "-lint", path], capture_output=True).returncode, 0)
                self.assertEqual(calls[-1][:2], ["launchctl", "bootstrap"])
                self.assertEqual(m.watch_service(False)[0], "removed")
                self.assertFalse(os.path.exists(path))
            finally:
                os.environ.clear()
                os.environ.update(old)
