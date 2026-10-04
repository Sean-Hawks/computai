import io
import json
import os
import unittest

from tests import helpers


class Mcp(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(COMPUTAI_CONFIG_DIR=self.sb.config, COMPUTAI_DATA_DIR=self.sb.data,
                          CLAUDE_CONFIG_DIR=helpers.fixture("claude"), CODEX_HOME=helpers.fixture("codex"),
                          COMPUTAI_FAKE_NOW="1790000000")
        self.m = helpers.load()
        self.db = self.m.open_ledger()

    def tearDown(self):
        self.db.close()
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def talk(self, *msgs):
        out = io.StringIO()
        self.m.serve_mcp(self.db, io.StringIO("".join(json.dumps(x) + "\n" for x in msgs) + "not json\n"), out)
        return [json.loads(x) for x in out.getvalue().splitlines()]

    def test_session(self):
        r = self.talk({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                      {"jsonrpc": "2.0", "method": "notifications/initialized"},
                      {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                      {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                       "params": {"name": "usage_summary", "arguments": {"month": "2026-09"}}},
                      {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "limits"}},
                      {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "nope"}},
                      {"jsonrpc": "2.0", "id": 6, "method": "nope"})
        self.assertEqual([x.get("id") for x in r], [1, 2, 3, 4, 5, 6, None])   # 通知沒有回應
        self.assertEqual(r[0]["result"]["serverInfo"]["name"], "computai")
        self.assertEqual({t["name"] for t in r[1]["result"]["tools"]},
                         {"usage_summary", "limits", "budget", "machines", "advice", "pick"})
        data = json.loads(r[2]["result"]["content"][0]["text"])
        self.assertEqual(data["month"], "2026-09")
        self.assertEqual({x["source"] for x in data["sources"]}, {"claude", "codex"})
        self.assertIn("limits", json.loads(r[3]["result"]["content"][0]["text"]))
        self.assertEqual(r[4]["error"]["code"], -32602)
        self.assertEqual(r[5]["error"]["code"], -32601)
        self.assertEqual(r[6]["error"]["code"], -32700)

    def test_non_object_input_does_not_end_the_session(self):
        r = self.talk([], 123, None, {"jsonrpc": "2.0", "id": 7, "method": "ping"})
        self.assertEqual(r[0]["id"], 7)
        self.assertEqual(r[0]["result"], {})

    def test_pick_tool(self):
        r = self.talk({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "pick", "arguments": {"task": "light"}}},
                      {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "pick", "arguments": {"task": "x"}}})
        data = json.loads(r[0]["result"]["content"][0]["text"])
        self.assertEqual(set(data), {"tool", "command", "reason", "ranked"})
        self.assertTrue(r[1]["result"]["isError"])

    def test_bad_month_is_tool_error(self):
        r = self.talk({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": "usage_summary", "arguments": {"month": "x"}}})
        self.assertTrue(r[0]["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
