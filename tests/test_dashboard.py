import os
import re
import unittest

from tests import helpers


class Dashboard(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(COMPUTAI_CONFIG_DIR=self.sb.config, COMPUTAI_DATA_DIR=self.sb.data,
                          COMPUTAI_FIXTURES=helpers.fixture("machines"), COMPUTAI_FAKE_NOW="1790000000")
        os.makedirs(self.sb.config)
        with open(os.path.join(self.sb.config, "config.ini"), "w") as f:
            f.write("[machines]\nmac = mac\n\n[machine.mac]\nservices = ollama:11434\nidle_watts = 6\n"
                    "max_watts = 30\n\n[power]\nidle_alert_minutes = 0\n")
        self.m = helpers.load()
        self.db = self.m.open_ledger()
        self.addCleanup(self.db.close)
        self.m.add_usage(self.db, [dict(source="claude", uid="1", ts=1789999000, model="claude-opus-5-5",
                                        project="/p/x", output=1000000)])
        self.m.add_limits(self.db, [dict(source="codex", name="week", ts=1789999000, used_percent=97.0,
                                         window_minutes=10080, resets_at=1790003600)])
        self.m.sample_machines(self.db)
        self.st = self.m.dashboard_state(self.db)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def test_state(self):
        st = self.st
        self.assertEqual(st["sources"][0]["source"], "claude")
        self.assertEqual(st["machines"][0]["machine"], "mac")
        self.assertEqual(st["machines"][0]["loaded"][0]["name"], "qwen3:0.6b")
        self.assertTrue(any(a["kind"] == "idle_model" for a in st["alerts"]))
        self.assertIn("Codex 97% (1h00m)", st["line_text"])

    def test_live_render_has_three_areas(self):
        text = self.m.render_live(self.st, 90)
        for title in ("Compute", "AI usage", "Alerts"):
            self.assertIn(title, text)
        self.assertIn("qwen3:0.6b on ollama", text)
        self.assertIn("! mac: qwen3:0.6b loaded but idle", text)
        self.assertNotIn("\033", text)                       # 沒開顏色就沒有控制碼
        self.assertIn("\033[1m", self.m.render_live(self.st, 90, color=True))

    def test_prometheus(self):
        text = self.m.prometheus(self.st)
        self.assertIn('computai_month_cost_usd{source="claude"} 20.0', text)
        self.assertIn('computai_limit_used_percent{source="codex",window="week"} 97.0', text)
        self.assertIn('computai_machine_power_watts{machine="mac"}', text)
        self.assertIn('computai_alerts{kind="idle_model"} 1.0', text)
        for ln in text.splitlines():                          # 每一行都是合法的格式
            self.assertTrue(ln.startswith("#") or re.match(r'^computai_\w+(\{[^}]*\})? -?[0-9.e+]+$', ln), ln)

    def test_label_escaping(self):
        self.assertEqual(self.m._prom_label('a"b\\c\nd'), 'a\\"b\\\\c\\nd')


if __name__ == "__main__":
    unittest.main()


class Clean(unittest.TestCase):
    def test_clean_strings(self):
        m = helpers.load()
        self.assertEqual(m.clean_strings({"a": ["x\x1b[2Jy", 3], "b": None}), {"a": ["x[2Jy", 3], "b": None})


class Web(unittest.TestCase):
    def setUp(self):
        import http.server
        import threading
        self.m = helpers.load()
        self.state = {"lock": threading.Lock(), "state": {"x": "<b>"}, "metrics": "computai_x 1.0\n"}
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), self.m.web_handler(self.state, "127.0.0.1", 5))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.port = self.srv.server_port

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()

    def get(self, path, host=None):
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request("GET", path, headers={"Host": host or "127.0.0.1:%d" % self.port})
        r = c.getresponse()
        body = r.read().decode()
        c.close()
        return r, body

    def test_pages(self):
        r, body = self.get("/")
        self.assertEqual(r.status, 200)
        self.assertIn('src="/app.js"', body)
        self.assertIn("frame-ancestors 'none'", r.getheader("Content-Security-Policy"))
        self.assertEqual(r.getheader("X-Content-Type-Options"), "nosniff")
        r, body = self.get("/app.js")
        self.assertIn("setInterval(tick, 5000)", body)
        self.assertNotIn("innerHTML", body)                 # 資料只用 textContent 放進頁面
        r, body = self.get("/api/state")
        self.assertEqual(body, '{"x": "<b>"}')
        r, body = self.get("/metrics")
        self.assertIn("version=0.0.4", r.getheader("Content-Type"))
        self.assertEqual(self.get("/nope")[0].status, 404)

    def test_dns_rebinding_blocked(self):
        self.assertEqual(self.get("/api/state", host="evil.example:8765")[0].status, 403)
        self.assertEqual(self.get("/api/state", host="localhost:8765")[0].status, 200)
        self.assertEqual(self.get("/api/state", host="[::1]:8765")[0].status, 200)
