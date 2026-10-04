import unittest

from tests import helpers

H = 3600


def w(name, used, resets_in, eta=None, minutes=None):
    return {"name": name, "used_percent": used, "resets_in": resets_in, "eta_full": eta,
            "window_minutes": minutes or (300 if name == "5h" else 10080)}


OLLAMA = [{"model": "qwen3:8b", "machine": "m1m", "command": "ssh m1m ollama run qwen3:8b", "busy": False}]

# (說明, subs, local, task, 該選的工具, 理由)
CASES = [
    ("快重置又還剩很多：先用掉",
     {"claude": [w("5h", 40, 40 * 60), w("week", 30, 3 * 86400)], "codex": [w("week", 5, 6 * 86400)]}, [], "heavy",
     "claude", "expiring"),
    ("快重置但只剩一點：不算",
     {"claude": [w("5h", 90, 40 * 60)], "codex": [w("week", 50, 5 * 86400)]}, [], "heavy", "codex", "headroom"),
    ("照速度會提早用完的避開",
     {"claude": [w("week", 20, 4 * 86400, eta=86400)], "codex": [w("week", 60, 4 * 86400)]}, [], "heavy",
     "codex", "headroom"),
    ("兩個都會提早用完：選剩比較多的",
     {"claude": [w("week", 20, 4 * 86400, eta=86400)], "codex": [w("week", 60, 4 * 86400, eta=3600)]}, [], "heavy",
     "claude", "early"),
    ("用完的永遠不選",
     {"claude": [w("week", 100, 2 * 86400)], "codex": [w("week", 95, 2 * 86400, eta=600)]}, [], "heavy",
     "codex", "early"),
    ("輕量任務：本地模型",
     {"claude": [w("week", 10, 4 * 86400)], "codex": [w("week", 10, 4 * 86400)]}, OLLAMA, "light",
     "local:qwen3:8b", "local_light"),
    ("輕量任務但有快重置的額度：先用額度",
     {"claude": [w("5h", 10, 30 * 60)]}, OLLAMA, "light", "claude", "expiring"),
    ("重的任務：本地模型最後才用",
     {"claude": [w("week", 10, 4 * 86400)]}, OLLAMA, "heavy", "claude", "headroom"),
    ("訂閱都用完：退到本地",
     {"claude": [w("week", 100, 86400)], "codex": [w("5h", 99.6, 3 * H)]}, OLLAMA, "heavy",
     "local:qwen3:8b", "local_fallback"),
    ("沒有額度資料但有裝：還是可以選",
     {"claude": []}, [], "heavy", "claude", "unknown"),
    ("Claude 額度不明，Codex 剩 44%：選已知額度",
     {"claude": [], "codex": [w("week", 56, 4 * 86400)]}, [], "heavy", "codex", "headroom"),
    ("Codex 額度不明，Claude 有剩：選已知額度",
     {"claude": [w("week", 56, 4 * 86400)], "codex": []}, [], "heavy", "claude", "headroom"),
    ("未知百分比不算成 100%",
     {"claude": [w("week", None, 4 * 86400)], "codex": [w("week", 56, 4 * 86400)]}, [], "heavy",
     "codex", "headroom"),
    ("已知額度會提早用完：仍優先於未知額度",
     {"claude": [], "codex": [w("week", 95, 4 * 86400, eta=H)]}, [], "heavy", "codex", "early"),
    ("已知額度用完：選未知額度作備用",
     {"claude": [], "codex": [w("week", 100, 4 * 86400)]}, [], "heavy", "claude", "unknown"),
    ("重任務：未知額度在本地模型前面",
     {"claude": []}, OLLAMA, "heavy", "claude", "unknown"),
    ("輕任務：本地模型仍在未知額度前面",
     {"claude": []}, OLLAMA, "light", "local:qwen3:8b", "local_light"),
    ("什麼都沒有",
     {"claude": None, "codex": [w("week", 100, 86400)]}, [], "heavy", None, "none"),
]


class Pick(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.m.set_lang("en")

    def test_rules(self):
        for desc, subs, local, task, tool, why in CASES:
            with self.subTest(desc):
                p = self.m.pick_agent(subs, local, task)
                self.assertEqual((p["tool"], p["why"]), (tool, why))
                self.assertTrue(self.m.pick_reason(p))

    def test_reason_and_command(self):
        p = self.m.pick_agent(CASES[0][1], [], "heavy")
        self.assertEqual(p["command"], "claude")
        self.assertEqual(self.m.pick_reason(p), "Claude Code 5-hour limit resets in 40m with 60% left - use it now or lose it")
        p = self.m.pick_agent({}, OLLAMA, "light")
        self.assertEqual(p["command"], "ssh m1m ollama run qwen3:8b")

    def test_unknown_has_no_invented_headroom(self):
        for windows in ([], [w("week", None, 4 * 86400)]):
            with self.subTest(windows=windows):
                p = self.m.pick_agent({"claude": windows, "codex": []}, OLLAMA, "heavy")
                self.assertEqual(p["why"], "unknown")
                self.assertEqual(p["args"], {"src": "claude"})
                self.assertEqual(p["ranked"], ["claude", "codex", "local:qwen3:8b"])
                for lang, reason in (("en", "Claude Code limit usage is unknown; selected as a fallback"),
                                     ("zh", "Claude Code 額度不明，作為備用選項")):
                    self.m.set_lang(lang)
                    self.assertEqual(self.m.pick_reason(p), reason)

    def test_known_headroom_ranks_before_unknown(self):
        for used in (0, 56, 99):
            with self.subTest(used=used):
                p = self.m.pick_agent({"claude": [], "codex": [w("week", used, 4 * 86400)]}, OLLAMA, "heavy")
                self.assertEqual(p["ranked"], ["codex", "claude", "local:qwen3:8b"])
                self.assertEqual(p["args"]["left"], 100 - used)

    def test_known_window_still_applies_with_unknown_window(self):
        for used, tool in ((56, "codex"), (100, "claude")):
            with self.subTest(used=used):
                p = self.m.pick_agent({"claude": [], "codex": [w("5h", None, H), w("week", used, 4 * 86400)]}, [], "heavy")
                self.assertEqual(p["tool"], tool)


class PickQuoting(unittest.TestCase):
    def test_model_names_cannot_run_commands_on_the_other_side(self):
        import os
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        old = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old)))
        os.environ.update(sb.env())
        m = helpers.load()
        m.machines = lambda: [{"name": "box", "host": "box"}]
        m.latest_samples = lambda db: [{"machine": "box", "age": 5, "services": [],
                                        "loaded": [{"service": "ollama", "name": "x; touch /tmp/pwned"}]}]
        db = m.open_ledger(":memory:")
        self.addCleanup(db.close)
        _subs, local = m.pick_inputs(db)
        self.assertEqual(local[0]["command"], "ssh box ollama run 'x; touch /tmp/pwned'")


class PickInsight(unittest.TestCase):
    def test_home_suggests_using_a_limit_that_resets_soon(self):
        import os
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        old = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old)))
        os.environ.update(sb.env(COMPUTAI_FAKE_NOW="1790000000"))
        m = helpers.load()
        m.set_lang("en")
        db = m.open_ledger()
        self.addCleanup(db.close)
        t = 1790000000
        m.add_limits(db, [{"source": "claude", "name": "5h", "ts": t - 60, "used_percent": 40.0, "window_minutes": 300,
                           "resets_at": t + 40 * 60}])
        texts = [x["text"] for x in m.insights(db, t) if x["kind"] == "pick"]
        self.assertEqual(texts, ["Claude Code 5-hour limit resets in 40m with 60% left - use it now or lose it"])


class PickCommand(unittest.TestCase):
    def test_shell_output_is_just_the_command(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        r = sb.run("--pick", PATH="/usr/bin:/bin")
        self.assertEqual((r.returncode, r.stdout), (1, ""))           # 沒有任何工具：不印指令，exit 1
        self.assertIn("nothing to pick", r.stderr)


if __name__ == "__main__":
    unittest.main()
