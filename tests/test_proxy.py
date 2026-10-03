import http.server
import json
import os
import threading
import unittest
import urllib.error
import urllib.request

from tests import helpers

FX = helpers.fixture("proxy")


def read(name):
    with open(os.path.join(FX, name), "rb") as f:
        return f.read()


class Meter(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()

    def meter(self, name, ctype, step=7):
        mt = self.m.UsageMeter(ctype)
        data = read(name)
        for i in range(0, len(data), step):     # 故意切在奇怪的地方，模擬網路分段
            mt.feed(data[i:i + step])
        self.assertTrue(mt.finish())
        return mt

    def test_ollama_stream(self):
        mt = self.meter("ollama-chat.ndjson", "application/x-ndjson")
        self.assertEqual((mt.prompt, mt.completion, mt.model), (11, 10, "qwen3:0.6b"))

    def test_ollama_json(self):
        mt = self.meter("ollama-generate.json", "application/json; charset=utf-8")
        self.assertEqual((mt.prompt, mt.completion), (12, 20))

    def test_openai_stream_with_cache(self):
        mt = self.meter("openai-stream.sse", "text/event-stream")
        self.assertEqual((mt.prompt, mt.completion, mt.cached), (30, 7, 16))

    def test_openai_json(self):
        mt = self.meter("openai.json", "application/json")
        self.assertEqual((mt.prompt, mt.completion), (11, 10))

    def test_responses_api(self):
        mt = self.meter("responses-stream.sse", "text/event-stream")
        self.assertEqual((mt.prompt, mt.completion, mt.model), (40, 9, "local-model"))

    def test_other_content_ignored(self):
        mt = self.m.UsageMeter("text/html")
        mt.feed(b"<html>usage eval_count</html>")
        self.assertFalse(mt.finish())

    def test_inject_include_usage(self):
        body = json.dumps({"model": "m", "stream": True, "messages": []}).encode()
        out, model = self.m.prepare_request(body, "/v1/chat/completions")
        self.assertEqual(model, "m")
        self.assertEqual(json.loads(out)["stream_options"], {"include_usage": True})
        same, _ = self.m.prepare_request(body, "/api/chat")
        self.assertEqual(same, body)
        same, _ = self.m.prepare_request(body, "/v1/chat/completions", inject=False)
        self.assertEqual(same, body)
        self.assertEqual(self.m.prepare_request(b"not json", "/x"), (b"not json", None))

    def test_parse_listen(self):
        p = self.m.parse_listen
        self.assertEqual(p("9000", 1), ("127.0.0.1", 9000))
        self.assertEqual(p(":9000", 1), ("127.0.0.1", 9000))
        self.assertEqual(p("0.0.0.0:9000", 1), ("0.0.0.0", 9000))
        self.assertEqual(p("[::1]:9000", 1), ("::1", 9000))
        self.assertEqual(p("", 1), ("127.0.0.1", 1))
        self.assertTrue(self.m.is_loopback("127.0.0.1"))
        self.assertFalse(self.m.is_loopback("0.0.0.0"))


class FakeUpstream(http.server.BaseHTTPRequestHandler):
    """依路徑回 fixture；/api/chat 用 chunked 串流回應。記下收到的請求。"""
    protocol_version = "HTTP/1.1"
    seen = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        FakeUpstream.seen.append((self.path, json.loads(self.rfile.read(n) or b"{}"),
                                  self.headers.get("Authorization"), self.headers.get("Accept-Encoding")))
        if self.path == "/api/chat":
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            for line in read("ollama-chat.ndjson").splitlines(True):
                self.wfile.write(b"%x\r\n%s\r\n" % (len(line), line))
            self.wfile.write(b"0\r\n\r\n")
            return
        name, ctype = {"/v1/chat/completions": ("openai.json", "application/json"),
                       "/api/generate": ("ollama-generate.json", "application/json")}.get(
            self.path, (None, None))
        if not name:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        body = read(name)
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class EndToEnd(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(COMPUTAI_CONFIG_DIR=self.sb.config, COMPUTAI_DATA_DIR=self.sb.data)
        self.m = helpers.load()
        FakeUpstream.seen = []
        self.up = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeUpstream)
        threading.Thread(target=self.up.serve_forever, daemon=True).start()
        handler, self.holder = self.m.make_proxy("http://127.0.0.1:%d" % self.up.server_port, "box")
        self.px = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.px.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self.px.server_port

    def tearDown(self):
        for s in (self.px, self.up):
            s.shutdown()
            s.server_close()
        self.holder["db"].close()
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def post(self, path, body, headers=None):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(),
                                     headers=dict({"Content-Type": "application/json"}, **(headers or {})))
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read()

    def test_counts_tokens_and_passes_through(self):
        status, body = self.post("/api/chat", {"model": "qwen3:0.6b", "messages": []})
        self.assertEqual(status, 200)
        self.assertEqual(body, read("ollama-chat.ndjson"))          # 原樣轉送
        self.post("/api/generate", {"model": "qwen3:0.6b", "prompt": "x", "stream": False})
        self.post("/v1/chat/completions", {"model": "qwen3:0.6b", "stream": True, "messages": []},
                  {"Authorization": "Bearer local-key"})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.post("/nope", {})
        cm.exception.close()
        db = self.m.open_ledger()
        rows = db.execute("SELECT model, input, output, project, cost_usd FROM usage ORDER BY rowid").fetchall()
        db.close()
        self.assertEqual([tuple(r) for r in rows], [("qwen3:0.6b", 11, 10, "box", 0.0),
                                                    ("qwen3:0.6b", 12, 20, "box", 0.0),
                                                    ("qwen3:0.6b", 11, 10, "box", 0.0)])
        path, sent, auth, enc = FakeUpstream.seen[2]
        self.assertEqual(enc, "identity")                          # 不讓上游壓縮回應
        self.assertEqual(sent["stream_options"], {"include_usage": True})
        self.assertEqual(auth, "Bearer local-key")                  # 金鑰照樣轉給上游

    def test_metrics_counters(self):
        self.post("/api/chat", {"model": "qwen3:0.6b", "messages": []})
        self.post("/api/generate", {"model": "qwen3:0.6b", "prompt": "x", "stream": False})
        for _ in range(40):
            if self.holder["totals"].get("qwen3:0.6b", [0, 0])[1] >= 30:
                break
            __import__("time").sleep(0.05)
        with urllib.request.urlopen(self.base + "/metrics", timeout=10) as r:
            text = r.read().decode()
        vals = self.m.parse_prom(text)                              # 取樣端用同一個解析器讀
        self.assertEqual(vals[("prompt", "qwen3:0.6b")], 23)
        self.assertEqual(vals[("generation", "qwen3:0.6b")], 30)

    def test_counters_only_when_machine_is_sampled(self):
        handler, holder = self.m.make_proxy("http://127.0.0.1:%d" % self.up.server_port, "box", ledger=False)
        px = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=px.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request("http://127.0.0.1:%d/api/chat" % px.server_port,
                                         data=json.dumps({"model": "qwen3:0.6b", "messages": []}).encode(),
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10).read()
            for _ in range(40):                 # proxy 送完回應才記，稍等一下
                if holder["totals"]:
                    break
                __import__("time").sleep(0.05)
            self.assertEqual(holder["totals"], {"qwen3:0.6b": [11, 10]})
            db = self.m.open_ledger()
            self.assertEqual(db.execute("SELECT COUNT(*) FROM usage").fetchone()[0], 0)   # 不重複記帳
            db.close()
        finally:
            px.shutdown()
            px.server_close()
            holder["db"].close()

    def test_rebinding_host_rejected(self):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", self.px.server_port, timeout=10)
        c.request("POST", "/api/generate", body=b"{}", headers={"Host": "evil.example:11435"})
        r = c.getresponse()
        r.read()
        c.close()
        self.assertEqual(r.status, 403)
        self.assertEqual(FakeUpstream.seen, [])

    def test_upstream_down(self):
        self.up.shutdown()
        self.up.server_close()
        handler, holder = self.m.make_proxy("http://127.0.0.1:9", "box")
        px = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=px.serve_forever, daemon=True).start()
        try:
            req = urllib.request.Request("http://127.0.0.1:%d/api/chat" % px.server_port, data=b"{}")
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(req, timeout=10)
            self.assertEqual(cm.exception.code, 502)
            cm.exception.close()
        finally:
            px.shutdown()
            px.server_close()
            holder["db"].close()
        self.up = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeUpstream)  # 讓 tearDown 有東西可關
        threading.Thread(target=self.up.serve_forever, daemon=True).start()


if __name__ == "__main__":
    unittest.main()
