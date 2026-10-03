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

    def step(self, limits, alerts=(), t=100000):
        return self.m.notify_events(self.db, {"limits": limits, "alerts": list(alerts), "forecast": {}, "time": t})

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

    def test_unreachable_waits_and_does_not_flap(self):
        a = {"kind": "machine_unreachable", "machine": "wsl", "message": "wsl: ssh timeout ..."}
        self.step([], t=0)
        self.assertEqual(self.step([], [a], t=60), [])                  # 剛斷線：先不吵
        self.assertEqual(self.step([], [a], t=400), [])
        ev = self.step([], [a], t=700)                                   # 斷了 10 分鐘以上才講
        self.assertEqual(ev, [("fail", "wsl has been unreachable for 10m (asleep, off, or Tailscale/VPN down?)")])
        self.assertEqual(self.step([], [a], t=760), [])                  # 講過了
        self.step([], [], t=800)                                         # 恢復
        self.step([], [a], t=900)                                        # 又斷
        self.assertEqual(self.step([], [a], t=2000), [])                 # 6 小時內不再講
        self.step([], [], t=3000)
        self.step([], [a], t=30000)
        self.assertEqual(len(self.step([], [a], t=31000)), 1)            # 冷卻過了才再講

    def test_other_alerts_right_away(self):
        a = {"kind": "idle_model", "machine": "mac", "message": "mac: model idle"}
        self.step([], t=0)
        self.assertEqual(self.step([], [a], t=10), [("warn", "mac: model idle")])

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
