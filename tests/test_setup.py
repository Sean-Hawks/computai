import os
import unittest
from unittest import mock

from tests import helpers

TEXT = """# my settings
[plans]
# what I pay
claude = Pro, 20, x

[power]
price_per_kwh = 3.2   ; summer
"""


class EditIni(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()

    def test_replace_keeps_comments(self):
        out = self.m.edit_ini(TEXT, "plans", "claude", "Max 5x, 100, 2026-10-03")
        self.assertIn("# what I pay\nclaude = Max 5x, 100, 2026-10-03\n", out)
        self.assertIn("# my settings", out)
        self.assertIn("price_per_kwh = 3.2   ; summer", out)

    def test_add_key_after_last_value(self):
        out = self.m.edit_ini(TEXT, "plans", "codex", "Plus, 20, x")
        self.assertIn("claude = Pro, 20, x\ncodex = Plus, 20, x\n\n[power]", out)

    def test_add_section(self):
        out = self.m.edit_ini(TEXT, "machine.wsl", "base_watts", "60")
        self.assertTrue(out.endswith("\n\n[machine.wsl]\nbase_watts = 60\n"))
        self.assertEqual(self.m.edit_ini("", "a", "b", "c"), "[a]\nb = c\n")

    def test_delete(self):
        out = self.m.edit_ini(TEXT, "plans", "claude", None)
        self.assertNotIn("claude", out)
        self.assertIn("# what I pay", out)
        self.assertEqual(self.m.edit_ini(TEXT, "nope", "x", None), TEXT)

    def test_key_with_regex_chars_and_similar_names(self):
        text = "[machines]\nbox = 1.2.3.4\nbox-2 = 5.6.7.8\n"
        out = self.m.edit_ini(text, "machines", "box", "9.9.9.9")
        self.assertEqual(out, "[machines]\nbox = 9.9.9.9\nbox-2 = 5.6.7.8\n")

    def test_parse_assignment(self):
        self.assertEqual(self.m.parse_assignment("machine.wsl.mac=aa:bb"), ("machine.wsl", "mac", "aa:bb"))
        with self.assertRaises(SystemExit):
            self.m.parse_assignment("nodot=1")


class SetCli(unittest.TestCase):
    def test_set_and_unset(self):
        sb = helpers.Sandbox()
        try:
            r = sb.run("--set", "plans.claude=Max 5x, 100, 2026-10-03", "--set", "power.currency=TWD")
            self.assertEqual(r.returncode, 0, r.stderr)
            path = os.path.join(sb.config, "config.ini")
            text = open(path, encoding="utf-8").read()
            self.assertIn("claude = Max 5x, 100, 2026-10-03", text)
            self.assertIn("currency = TWD", text)
            self.assertIn("# ComputAI settings", text)              # 範本的註解還在
            self.assertTrue(os.path.exists(path + ".bak"))
            sb.run("--unset", "plans.claude")
            self.assertNotIn("claude = Max 5x", open(path, encoding="utf-8").read())
        finally:
            sb.close()


if __name__ == "__main__":
    unittest.main()


class PlanHint(unittest.TestCase):
    def test_missing_plan_hint_uses_detected_plan(self):
        m = helpers.load()
        db = m.open_ledger(":memory:")
        m.add_usage(db, [dict(source="codex", uid="1", ts=100, model="gpt-5.5", output=10)])
        m.add_limits(db, [dict(source="codex", name="week", ts=90, used_percent=5.0, plan="pro")])
        s = m.summary(db, 0, 1000, plan_table={})
        self.assertTrue(s["sources"][0]["plan_missing"])
        self.assertEqual(s["sources"][0]["plan_detected"], "pro")
        self.assertIn("plan: not set (the logs say 'pro') - run `computai --setup`", m.render_summary(s))
        s = m.summary(db, 0, 1000, plan_table={"codex": {"name": "Pro", "usd": 200.0, "checked": ""}})
        self.assertNotIn("plan_missing", s["sources"][0])
        db.close()

    def test_default_template_has_no_plans(self):
        m = helpers.load()
        cp = m._ini()
        cp.read_string(m.DEFAULT_CONFIG)
        self.assertEqual(cp.items("plans"), [])


class Doctor(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.makedirs(self.sb.config)
        with open(os.path.join(self.sb.config, "config.ini"), "w") as f:
            f.write("[machines]\nmac = mac\ngone = nowhere\n\n[machine.mac]\nservices = ollama:11434\n\n"
                    "[power]\ncurrency = TWD\n")
        os.environ.update(COMPUTAI_CONFIG_DIR=self.sb.config, COMPUTAI_DATA_DIR=self.sb.data,
                          COMPUTAI_FIXTURES=helpers.fixture("machines"), CLAUDE_CONFIG_DIR=helpers.fixture("claude"),
                          CODEX_HOME=os.path.join(self.sb.root, "none"))
        self.m = helpers.load()
        self.db = self.m.open_ledger()

    def tearDown(self):
        self.db.close()
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def test_findings(self):
        self.m.sync(self.db, quiet=True)
        items = self.m.doctor(self.db)
        by = {}
        for x in items:
            by.setdefault(x["area"], []).append(x)
        self.assertEqual(by["claude"][0]["level"], "ok")
        self.assertEqual(by["codex"][0]["level"], "tip")                      # 沒有 Codex 的 log
        plan = [x for x in by["plans"] if "claude" in x["text"]][0]
        self.assertEqual((plan["level"], plan["fix"]), ("todo", "computai --setup"))
        sl = [x for x in by["claude"] if "status" in x["text"]][0]
        self.assertEqual(sl["level"], "todo")
        pw = [x for x in by["machine:mac"] if x["fix"].startswith("computai --set")][0]
        self.assertIn("--set machine.mac.idle_watts=5 --set machine.mac.max_watts=30", pw["fix"])
        self.assertTrue(any("proxy" in x["fix"] for x in by["machine:mac"]))
        self.assertEqual(by["machine:gone"][0]["level"], "todo")
        self.assertEqual(by["power"][0]["level"], "todo")                    # TWD 沒有匯率
        text = self.m.render_doctor(items)
        self.assertEqual(text.count("Claude Code\n"), 1)                      # 同一類只出現一次
        self.assertIn("thing(s) to set up", text)

    def test_statusline_detection(self):
        os.makedirs(os.path.join(self.sb.root, "cc"))
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.sb.root, "cc")
        with open(os.path.join(self.sb.root, "cc", "settings.json"), "w") as f:
            f.write('{"statusLine": {"type": "command", "command": "computai --statusline"}, "x": 1}')
        self.assertEqual(self.m.claude_statusline(), "computai --statusline")


class DiscoverAdd(unittest.TestCase):
    def test_add_machines(self):
        sb = helpers.Sandbox()
        old = dict(os.environ)
        try:
            os.makedirs(sb.config)
            with open(os.path.join(sb.config, "config.ini"), "w") as f:
                f.write("# mine\n[machines]\nmac = othermac\n")
            os.environ.update(COMPUTAI_CONFIG_DIR=sb.config, COMPUTAI_FIXTURES=helpers.fixture("machines"))
            m = helpers.load()
            found = [{"name": "mac", "host": "mac", "ok": True, "configured": False},
                     {"name": "gpubox", "host": "gpubox", "ok": True, "configured": False},
                     {"name": "dead", "host": "dead", "ok": False, "configured": False},
                     {"name": "old", "host": "old", "ok": True, "configured": True}]
            added = m.add_machines(found)
            self.assertEqual([(a["name"], a["host"]) for a in added], [("mac-2", "mac"), ("gpubox", "gpubox")])
            text = open(os.path.join(sb.config, "config.ini"), encoding="utf-8").read()
            self.assertIn("# mine", text)
            self.assertIn("mac-2 = mac", text)
            self.assertIn("[machine.mac-2]\nidle_watts = 5\nmax_watts = 30", text)
            self.assertIn("[machine.gpubox]\nbase_watts = 60\ncpu_watts = 90", text)
        finally:
            os.environ.clear()
            os.environ.update(old)
            sb.close()


class Wizard(unittest.TestCase):
    def setUp(self):
        import shutil
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.makedirs(self.sb.config)
        with open(os.path.join(self.sb.config, "config.ini"), "w") as f:
            f.write("# keep me\n[machines]\nmac = mac\n\n[machine.mac]\nservices = ollama:11434\n")
        self.cc = os.path.join(self.sb.root, "claude")
        shutil.copytree(helpers.fixture("claude"), self.cc)
        os.environ.update(COMPUTAI_CONFIG_DIR=self.sb.config, COMPUTAI_DATA_DIR=self.sb.data,
                          COMPUTAI_FIXTURES=helpers.fixture("machines"), CLAUDE_CONFIG_DIR=self.cc,
                          CODEX_HOME=os.path.join(self.sb.root, "none"), COMPUTAI_FAKE_NOW="1790000000")
        for k in ("RUNPOD_API_KEY",):
            os.environ.pop(k, None)
        self.m = helpers.load()
        self.m.discover = lambda: [{"name": "gpubox", "host": "gpubox", "ok": True, "configured": False,
                                    "info": "Linux x86_64 + NVIDIA"},
                                   {"name": "dead", "host": "dead", "ok": False, "configured": False,
                                    "info": "timed out"}]
        self.db = self.m.open_ledger()
        self.m.sync(self.db, quiet=True)

    def tearDown(self):
        self.db.close()
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def run_wizard(self, answers, secrets=()):
        answers, secrets, out = list(answers), list(secrets), []
        w = self.m.Setup(self.db, ask=lambda p: answers.pop(0), secret_ask=lambda p: secrets.pop(0) if secrets else "",
                         out=out.append)
        code = w.run()
        self.assertEqual(answers, [], "unused answers")
        return code, "\n".join(map(str, out))

    def test_full_run(self):
        import json
        import stat
        code, text = self.run_wizard(
            ["", "classic", "2", "c", "My Plus", "20", "", "y", "all", "y", "100,50", "2", "31.5", "300", "y", ""],
            secrets=["rp_SECRET"])
        self.assertEqual(code, 0)
        cfg = open(os.path.join(self.sb.config, "config.ini"), encoding="utf-8").read()
        self.assertIn("# keep me", cfg)
        self.assertIn("claude = Claude Max 5x, 100, 2026-09-21", cfg)
        self.assertIn("codex = My Plus, 20, 2026-09-21", cfg)
        self.assertIn("gpubox = gpubox", cfg)
        self.assertIn("[machine.mac]\nservices = ollama:11434\nidle_watts = 5\nmax_watts = 30", cfg)
        self.assertIn("[machine.gpubox]\nbase_watts = 100\ncpu_watts = 50", cfg)
        self.assertIn("tariff = tou", cfg)
        self.assertIn("usd_to_local = 31.5", cfg)
        self.assertIn("monthly_usd = 300", cfg)
        self.assertIn("theme = classic", cfg)
        sec = os.path.join(self.sb.config, "secrets.ini")
        self.assertEqual(stat.S_IMODE(os.stat(sec).st_mode), 0o600)
        self.assertIn("RUNPOD_API_KEY = rp_SECRET", open(sec).read())
        self.assertNotIn("rp_SECRET", text)                       # 確認畫面上不會出現金鑰
        settings = json.load(open(os.path.join(self.cc, "settings.json")))
        self.assertTrue(settings["statusLine"]["command"].endswith("--statusline"))

    def test_wraps_existing_statusline_and_keeps_settings(self):
        import json
        with open(os.path.join(self.cc, "settings.json"), "w") as f:
            json.dump({"statusLine": {"type": "command", "command": "~/bin/my-line"}, "theme": "dark"}, f)
        code, _ = self.run_wizard(["", "", "s", "s", "y", "n", "", "s", "", "", ""])
        self.assertEqual(code, 0)
        settings = json.load(open(os.path.join(self.cc, "settings.json")))
        self.assertEqual(settings["theme"], "dark")
        script = settings["statusLine"]["command"]
        body = open(script).read()
        self.assertIn("~/bin/my-line", body)
        self.assertIn("--statusline", body)
        self.assertTrue(os.path.exists(os.path.join(self.cc, "settings.json.computai.bak")))

    def test_skip_everything_changes_nothing(self):
        before = open(os.path.join(self.sb.config, "config.ini")).read()
        code, text = self.run_wizard(["", "", "s", "s", "n", "n", "s", "", "", "n"])
        self.assertEqual(code, 0)
        self.assertIn("Nothing changed", text)
        self.assertEqual(open(os.path.join(self.sb.config, "config.ini")).read(), before)

    def test_cancel_saves_nothing(self):
        before = open(os.path.join(self.sb.config, "config.ini")).read()
        code, _ = self.run_wizard(["", "", "1", "s", "n", "n", "s", "", "", "n", "n"])
        self.assertEqual(code, 1)
        self.assertEqual(open(os.path.join(self.sb.config, "config.ini")).read(), before)

    def test_needs_terminal(self):
        r = self.sb.run("--setup")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("needs a terminal", r.stderr)


class Lang(unittest.TestCase):
    def test_auto_from_environment(self):
        old = dict(os.environ)
        try:
            m = helpers.load()
            os.environ["LANG"] = "zh_TW.UTF-8"
            self.assertEqual(m.system_lang(), "zh")
            for apple, want in (('(\n    "en-US"\n)', "en"), ('(\n    "zh-Hant-TW"\n)', "zh")):
                m = helpers.load()
                os.environ.pop("COMPUTAI_FIXTURES", None)
                m.run_cmd = lambda *a, **k: apple
                os.environ["LANG"] = "en_US.UTF-8"                # cmux／Ghostty 的預設，不代表使用者的選擇
                with mock.patch.object(m.sys, "platform", "darwin"):
                    self.assertEqual(m.system_lang(), want)
            os.environ["COMPUTAI_LANG"] = "zh"
            self.assertEqual(m.system_lang(), "zh")               # 環境變數直接指定
            cp = m._ini()
            cp.read_string("[general]\nlang = zh\n")
            self.assertEqual(m.config_lang(cp), "zh")             # 明確指定的優先
        finally:
            os.environ.clear()
            os.environ.update(old)
