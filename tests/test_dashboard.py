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

    def test_history_and_daily(self):
        os.environ["COMPUTAI_FAKE_NOW"] = "1790000060"
        self.m.sample_machines(self.db)
        mac = self.m.latest_samples(self.db)[0]
        self.assertEqual(len(mac["history"]["gpu"]), 2)
        self.assertEqual(mac["host"], "mac")
        self.assertEqual(mac["gpus"][0]["model"], "Apple M3 10-core")
        self.assertEqual(len(mac["gpus"][0]["history"]), 2)
        self.assertEqual(mac["mem_total"], 16384)
        d = self.m.daily_costs(self.db, 3)
        self.assertEqual(len(d["days"]), 3)
        self.assertEqual(d["sources"]["claude"][-1], 20.0)   # 今天（9/21）那筆 $20

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


class Report(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()

    def tearDown(self):
        self.sb.close()

    def test_html_report(self):
        env = dict(CLAUDE_CONFIG_DIR=helpers.fixture("claude"), CODEX_HOME=helpers.fixture("codex"),
                   COMPUTAI_FAKE_NOW="1790000000")
        out = os.path.join(self.sb.root, "r.html")
        r = self.sb.run("--report", "--month", "2026-09", "--html", out, **env)
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as f:
            html = f.read()
        self.assertIn("<h1>ComputAI report 2026-09</h1>", html)
        # 9/9 codex、9/10 claude+codex、9/11 claude、9/12 claude：每一段長條都有 hover 提示
        self.assertEqual(html.count("<title>2026-09-"), 5)
        self.assertIn("<td>2026-09-01</td>", html)                # 沒用量的日子也在表格裡
        self.assertIn("demo/alpha", html)
        self.assertNotIn("FAKE", html)
        text = self.sb.run("--report", "--month", "2026-09", "--no-sync", **env)
        self.assertIn("by project", text.stdout)
        self.assertIn("Cache efficiency", text.stdout)

    def test_escaping(self):
        m = helpers.load()
        days = [{"day": "2026-09-01", "claude": 1.0, "codex": 0, "cloud": 0, "other": 0}]
        self.assertIn("<title>2026-09-01 claude: $1.00</title>", m._svg_days(days))
        r = {"summary": {"range": {"start": 0, "end": 86400, "label": "<x>"}, "sources": [], "total_cost_usd": 0},
             "days": [], "projects": [{"project": "/a/<script>", "source": "claude", "requests": 1, "cost_usd": 1}],
             "machines": [], "analysis": {"range": {"label": ""}, "forecast": {"projected_usd": 0},
                                          "plans": [], "cache": {"hit_ratio": None, "rewrites": 0, "expired": 0,
                                                                 "wasted_usd": 0, "sessions": []}, "machines": []},
             "limits": []}
        m.render_analysis = lambda a: "ok"
        html = m.render_report_html(r)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class DefaultAction(unittest.TestCase):
    def test_only_bare_command_goes_live(self):
        m = helpers.load()
        called = []
        m.run_live = lambda *a: called.append("live") or 0
        import sys
        real = (sys.stdout, sys.stdin)
        tty = type("Tty", (), {"isatty": lambda self: True, "write": lambda self, s: None,
                               "flush": lambda self: None})()
        sys.stdout = sys.stdin = tty
        self.addCleanup(lambda: setattr(sys, "stdout", real[0]) or setattr(sys, "stdin", real[1]))
        m.summary = lambda *a, **k: called.append("summary") or {"sources": []}
        db = m.open_ledger(":memory:")
        try:
            m.run(m.parse_args([]), db)
            self.assertEqual(called, ["live"])
            for argv in (["--month", "2026-09"], ["--by", "project"]):
                called[:] = []
                m.sync = lambda *a, **k: {}
                try:
                    m.run(m.parse_args(argv + ["--no-sync"]), m.open_ledger(":memory:"))
                except Exception:
                    pass
                self.assertNotIn("live", called, argv)
        finally:
            db.close()
