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
        self.assertIn("Codex 3% left (1h00m)", st["line_text"])
        self.assertEqual(st["verdict"]["level"], "warn")              # 97% 和閒置的模型：注意
        self.assertEqual(st["verdict"]["items"][0][0], "warn")

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
        for title in ("COMPUTE", "AI SUBSCRIPTIONS", "ALERTS", "\u2500 mac "):
            self.assertIn(title, text)
        self.assertIn("ollama:11434", text)
        self.assertIn("qwen3:0.6b", text)
        self.assertIn("mac: qwen3:0.6b is loaded but has not been used", text)
        self.assertIn("free the memory", text)                  # 長的警示會折行，不會被切掉
        self.assertTrue(all(self.m.vlen(ln) <= 90 for ln in text.splitlines()))
        wide = self.m.render_live(self.st, 160)
        self.assertTrue(any("COMPUTE" in ln and "LOCAL MODELS" in ln for ln in wide.splitlines()))  # 兩欄
        ascii_ = self.m.render_live(self.st, 90, ascii_=True)
        self.assertTrue(all(ord(c) < 128 for c in ascii_), [c for c in ascii_ if ord(c) >= 128])
        self.assertNotIn("\033", text)                       # 沒開顏色就沒有控制碼
        self.assertIn("\033[1m", self.m.render_live(self.st, 90, color=True))

    def test_compact_when_short(self):
        text = self.m.render_live(self.st, 100, height=18)
        self.assertIn("MACHINES", text)
        self.assertNotIn("\u2500 mac ", text)
        self.assertIn("mac", text)
        self.assertIn("\u2500 mac ", self.m.render_live(self.st, 100, height=200))

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

    def test_calm_cyber_style(self):
        # docs/DESIGN.md：沒有掃描線、glitch、切角、霓虹光暈；總結列在最上面
        css, html = self.m.WEB_CSS, self.m.WEB_HTML
        for banned in ("glitch", "clip-path", "repeating-linear-gradient", "text-shadow"):
            self.assertNotIn(banned, css + html)
        self.assertLess(html.index('id="verdict"'), html.index('id="tiles"'))

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
        r["local"] = [{"model": "qwen<3>", "machine": "box", "via": "proxy", "prompt": 10, "output": 20, "requests": 1}]
        m.render_analysis = lambda a: "ok"
        html = m.render_report_html(r)
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("<td>qwen&lt;3&gt;</td><td>box</td><td>proxy</td>", html)


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


class Fits(unittest.TestCase):
    def test_fits(self):
        m = helpers.load()
        f = m.fits({"gpus": [{"vendor": "nvidia", "mem_total": 16376, "mem_used": 2729}]})
        self.assertEqual((f["free_gb"], f["params_b"], f["multi_gpu"]), (13.3, 14, False))
        two = m.fits({"gpus": [{"vendor": "nvidia", "mem_total": 24576, "mem_used": 0}] * 2})
        self.assertEqual((two["params_b"], two["multi_gpu"]), (70, True))   # 兩張 24 GB 合起來放得下 70B
        mac = m.fits({"mem_total": 32768, "mem_used": 20480, "gpus": [{"vendor": "apple", "mem_total": 32768}]})
        self.assertEqual((mac["free_gb"], mac["params_b"]), (9.0, 8))
        self.assertIsNone(m.fits({"gpus": []}))
        self.assertIsNone(m.fits({"gpus": [{"vendor": "nvidia", "mem_total": 16000, "mem_used": 15500}]})["params_b"])


class PerService(unittest.TestCase):
    def test_only_the_busy_service_shows_busy(self):
        sb = helpers.Sandbox()
        old = dict(os.environ)
        try:
            os.environ.update(COMPUTAI_CONFIG_DIR=sb.config, COMPUTAI_DATA_DIR=sb.data, COMPUTAI_FAKE_NOW="1000")
            m = helpers.load()
            db = m.open_ledger()
            svc = lambda kind, port, model, p, g, run: {"kind": kind, "port": port, "running": run,
                                                       "models": [{"name": model, "vram_mb": None}],
                                                       "counters": {model: {"prompt": p, "generation": g}}}
            d = lambda a, b: {"cpu": None, "gpus": [], "services": [svc("llamacpp", 8080, "q8", 10, 10, 0),
                                                                     svc("vllm", 8000, "qwen", a, b, 0)]}
            m.record_sample(db, {"name": "box"}, d(0, 0), 900)
            m.record_sample(db, {"name": "box"}, d(100, 600), 990)
            box = m.latest_samples(db, t=1000)[0]
            by = {x["kind"]: x for x in box["services"]}
            self.assertEqual((by["vllm"]["busy"], by["vllm"]["tok_s"]), (True, 10.0))
            self.assertEqual((by["llamacpp"]["busy"], by["llamacpp"]["tok_s"]), (False, 0.0))
            db.close()
        finally:
            os.environ.clear()
            os.environ.update(old)
            sb.close()


class Hud(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.m.set_lang("en")
        self.m.set_style(color=False, theme="cyber")
        self.st = {"machines": [{"machine": "wsl", "ai_active": True, "recent": {"tok_s": 296, "requests": 3},
                                 "gpus": [{"model": "RTX"}]}],
                   "limits": [{"source": "codex", "name": "week", "used_percent": 100.0, "resets_in": 3600,
                               "window_minutes": 10080}],
                   "sources": [{"source": "codex", "tokens": 1000}], "alerts": [], "today_usd": 9.5,
                   "forecast": {}}

    def test_ticker_scrolls_and_fits(self):
        a, b = self.m.ticker(self.st, 60, 0), self.m.ticker(self.st, 60, 5)
        self.assertNotEqual(a, b)
        self.assertIn("wsl generating 296 tok/s", a)
        self.assertTrue(self.m.vlen(a) <= 60 and self.m.vlen(b) <= 60)
        wide = self.m.ticker(self.st, 400, 3)                    # 比一圈還寬：接縫不能重複或缺字
        self.assertNotIn("wswsl", wide)
        self.assertNotIn("ww", wide.replace("worth", ""))

    def test_boot_reveals_real_checks(self):
        partial = self.m.render_boot(self.st, 80, 30, 2)
        self.assertIn("LEDGER", partial)
        self.assertNotIn("SYSTEM READY", partial)
        done = self.m.render_boot(self.st, 80, 30, 99)
        self.assertIn("GENERATING  RTX", done)
        self.assertIn("DEPLETED", done)
        self.assertIn("[ALERT]  SYSTEM READY", done)
        self.assertIn("linking", self.m.render_boot(None, 80, 30, 0))
