import json
import os
import unittest

from tests import helpers

ROOT = helpers.fixture("claude")


class ClaudeParser(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()

    def test_parse_main_session(self):
        rows = {r["uid"]: r for r in self.m.parse_claude_file(
            os.path.join(ROOT, "projects", "-home-demo-alpha", "sess-1.jsonl"))}
        self.assertEqual(sorted(rows), ["msg_A:req_A", "msg_B:req_B", "msg_C:req_C"])
        a = rows["msg_A:req_A"]
        self.assertEqual(a["output"], 377)          # 半截紀錄被完整版取代
        self.assertEqual(a["reasoning"], 120)
        self.assertEqual(a["cache_write_1h"], 200)
        self.assertEqual(a["cache_read"], 1000)
        self.assertEqual(a["project"], "/home/demo/alpha")
        self.assertEqual(a["subagent"], 0)
        self.assertEqual(rows["msg_B:req_B"]["model"], "claude-opus-5-5")   # 去掉 [1m]
        self.assertEqual(rows["msg_B:req_B"]["cache_write_5m"], 500)
        self.assertEqual(rows["msg_C:req_C"]["model"], "claude-opus-4-8@fast")

    def test_no_message_text_kept(self):
        rows = self.m.parse_claude_file(os.path.join(ROOT, "projects", "-home-demo-alpha", "sess-1.jsonl"))
        self.assertNotIn("FAKE", json.dumps(rows))

    def test_subagent_file(self):
        rows = self.m.parse_claude_file(os.path.join(
            ROOT, "projects", "-home-demo-alpha", "sess-1", "subagents", "agent-1.jsonl"))
        self.assertTrue(all(r["subagent"] == 1 for r in rows))


class ClaudeSync(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()

    def tearDown(self):
        self.sb.close()

    def test_sync_twice_counts_once(self):
        env = {"CLAUDE_CONFIG_DIR": ROOT}
        r = self.sb.run("--sync", **env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("claude   +4", r.stdout)
        os.utime(os.path.join(ROOT, "projects", "-home-demo-alpha", "sess-1.jsonl"))  # 強迫重讀
        self.sb.run("--sync", **env)
        d = json.loads(self.sb.run("--summary", "--month", "2026-09", "--json", **env).stdout)
        claude = d["sources"][0]
        self.assertEqual(claude["totals"]["requests"], 4)
        self.assertEqual(claude["totals"]["output"], 377 + 50 + 20 + 40)
        # msg_A: 3*4 + 1000*0.2 + 200*8 + 377*20 = 9352 / 1e6
        opus = [x for x in claude["models"] if x["model"] == "claude-opus-5-5"][0]
        self.assertAlmostEqual(opus["cost_usd"], (9352 + 10 * 4 + 500 * 5 + 50 * 20) / 1e6)


if __name__ == "__main__":
    unittest.main()
