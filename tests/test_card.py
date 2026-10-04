import os
import shutil
import subprocess
import time
import unittest
import xml.etree.ElementTree as ET

from tests import helpers
from tests.test_wrapped import PRICES, SECRET, SESSION, seed


class Card(unittest.TestCase):
    def setUp(self):
        if hasattr(time, "tzset"):
            os.environ["TZ"] = "UTC"
            time.tzset()
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)
        self.addCleanup(self.m.set_lang, "en")
        self.m.set_lang("en")
        seed(self.m, self.db)
        self.t = self.m.calendar_ts(2026, 9, 12, 12)

    def card(self, period="30d"):
        return self.m.card_data(self.db, period, PRICES, {}, t=self.t)

    def test_periods(self):
        sept = 4 * 3100000 + 500000 + 4000
        self.assertEqual(self.card("30d")["tokens"], sept + 1000000)      # 8/20 的那筆還在 30 天內
        self.assertEqual(self.card("month")["tokens"], sept)
        self.assertEqual(self.card("year")["tokens"], sept + 1000000)
        self.assertEqual(self.card("all")["tokens"], sept + 1000000)
        with self.assertRaises(SystemExit):
            self.card("week")

    def test_fields_and_bars(self):
        c = self.card("month")
        self.assertEqual((c["top_model"], c["active_days"], c["longest_streak"]), ("claude-opus-5-5", 5, 4))
        self.assertEqual(len(c["bars"]), 14)                              # 最近 14 天，最後一根是今天
        self.assertEqual(c["bars"][-1], 0.0)
        self.assertGreater(c["bars"][13 - 2], 0)                          # 9/10
        self.assertGreater(c["bars"][13 - 11], 0)                         # 9/1
        y = self.card("year")
        self.assertEqual(len(y["bars"]), 12)
        self.assertGreater(y["bars"][-1], 0)                              # 九月
        self.assertGreater(y["bars"][-2], 0)                              # 八月

    def test_svg_dark_and_light(self):
        c = self.card()
        dark, light = self.m.render_card_svg(c, "dark"), self.m.render_card_svg(c, "light")
        for svg in (dark, light):
            root = ET.fromstring(svg)
            self.assertEqual((root.get("width"), root.get("height")), ("900", "390"))
            for bad in ("<script", "<image", "href", "@font-face", "@import", "onload", "<foreignObject"):
                self.assertNotIn(bad, svg)
            self.assertEqual(svg.count("http"), 1)                        # 只有 xmlns
            for want in ("30D", "13.9M", "claude-opus-5-5", "SYS.COMPUTAI :: AI_OPS", "LOADOUT", "AGENT HOURS", "PEAK PARALLEL"):
                self.assertIn(want, svg)
            self.assertNotIn("secret", svg)
            self.assertNotIn(SESSION, svg)
        self.assertIn("#0a0a0f", dark)
        self.assertIn("#f7f7fb", light)
        self.assertIn("prefers-reduced-motion", dark)                    # 動畫可以被系統設定關掉
        self.assertNotEqual(dark, light)

    def test_escapes_model_and_zh(self):
        self.m.add_usage(self.db, [dict(source="claude", uid="evil", ts=self.m.calendar_ts(2026, 9, 11, 3),
                                        model='<b>"&', output=10 ** 11)])
        svg = self.m.render_card_svg(self.card())
        ET.fromstring(svg)
        self.assertNotIn("<b>", svg)
        self.m.set_lang("zh")
        svg = self.m.render_card_svg(self.card("year"), "light")
        ET.fromstring(svg)
        self.assertIn("今年", svg)

    def test_level_heatmap_and_badges(self):
        self.assertEqual(self.m.card_level(0), (0, 0, "INITIATE"))
        self.assertEqual(self.m.card_level(900e6)[:1], (30,))             # sqrt(900) = 30
        self.assertEqual(self.m.card_level(900e6)[2], "TOKEN ALCHEMIST")
        c = self.card()
        self.assertEqual(len(c["heat"]), 91)                               # 13 週 × 7 天
        self.assertEqual(len(c["pulse"]), 30)
        self.assertIsNone(c["heat"][-1]) if c["heat"][-1] is None else None
        self.assertTrue(any(v for v in c["heat"] if v))
        self.assertIn("STREAK x%d" % c["longest_streak"], c["badges"]) if c["longest_streak"] >= 7 else None
        svg = self.m.render_card_svg(c, handle="neo")
        self.assertIn("SYS.NEO :: AI_OPS", svg)

    def test_styles_and_custom_colors(self):
        c = self.card()
        svgs = {st: self.m.render_card_svg(c, style=st) for st in self.m.CARD_STYLES}
        self.assertEqual(len(set(svgs.values())), len(svgs))              # 每個主題長得不一樣
        self.assertIn("#00f0ff", svgs["netrunner"])                        # 預設 netrunner：霓虹青
        self.assertEqual(self.m.render_card_svg(c, style="computai"), svgs["netrunner"])   # 舊名稱還能用
        self.assertIn("#fbbf24", svgs["amber"])
        custom = self.m.render_card_svg(c, colors=("#123456", "#abcdef"))
        self.assertIn("#123456", custom)
        self.assertEqual(self.m.card_colors("#123456, #abcdef"), ("#123456", "#abcdef"))
        self.assertIsNone(self.m.card_colors("red, blue"))                # 格式不對就當沒設

    def test_flat_layouts_are_static_and_private_in_both_languages(self):
        c = self.card()
        c["models"][0]["model"] = '<script>"&' + "長模型" * 35 + "\x1b[2J"
        c["top_model"] = c["models"][0]["model"]
        for lang in ("en", "zh"):
            for theme in ("dark", "light"):
                for style in ("minimal", "paper", "github", "terminal"):
                    for layout, dims in (("compact", (720, 230)), ("dashboard", (900, 360)), ("portrait", (420, 610))):
                        with self.subTest(lang=lang, theme=theme, style=style, layout=layout):
                            svg = self.m.render_card_svg(c, theme, handle='<reader>&', lang=lang, style=style, layout=layout, t=self.t)
                            root = ET.fromstring(svg)
                            self.assertEqual((int(root.get("width")), int(root.get("height"))), dims)
                            for bad in ("<script", "<image", "href=", "@import", "@font-face", "animation:", "filter=", "\x1b", SECRET, SESSION):
                                self.assertNotIn(bad, svg)
                            self.assertIn("API 等值" if lang == "zh" else "API EQUIVALENT", svg)
                            self.assertIn("13.9M", svg)
                            for rect in root.findall("{http://www.w3.org/2000/svg}rect"):
                                self.assertGreaterEqual(float(rect.get("width")), 0)
                                self.assertLessEqual(float(rect.get("x")) + float(rect.get("width")), dims[0])
                                self.assertLessEqual(float(rect.get("y")) + float(rect.get("height")), dims[1])

    def test_style_defaults_and_empty_layouts(self):
        c = self.card()
        for style, layout in self.m.CARD_DEFAULT_LAYOUT.items():
            self.assertIn('data-layout="%s"' % layout, self.m.render_card_svg(c, style=style))
        self.assertEqual(self.m.render_card_svg(c), self.m.render_card_svg(c, layout="hud"))
        self.assertEqual(self.m.render_card_svg(c, style="mono"), self.m.render_card_svg(c))
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        empty = self.m.card_data(db, t=self.t)
        for layout in ("compact", "dashboard", "portrait"):
            svg = self.m.render_card_svg(empty, style="minimal", layout=layout, handle="reader", credit=False)
            root = ET.fromstring(svg)
            self.assertIn("No usage yet", svg)
            self.assertNotIn("ComputAI", "".join(root.itertext()))
        with self.assertRaises(ValueError):
            self.m.render_card_svg(c, layout="bad")

    @unittest.skipUnless(shutil.which("git"), "needs git")
    def test_handle_from_profile_repo(self):
        self.assertIsNone(self.m.github_owner(""))
        repo = os.path.join(self.sb.root, "profile") if hasattr(self, "sb") else None
        if repo is None:
            import tempfile
            repo = tempfile.mkdtemp()
            self.addCleanup(__import__("shutil").rmtree, repo)
        os.makedirs(repo, exist_ok=True)
        subprocess.run(["git", "init", "-q", repo], check=True)
        subprocess.run(["git", "-C", repo, "remote", "add", "origin", "git@github.com:octocat/octocat.git"], check=True)
        self.assertEqual(self.m.github_owner(repo), "octocat")
        svg = self.m.render_card_svg(self.card(), handle=self.m.github_owner(repo))
        self.assertIn("SYS.OCTOCAT :: AI_OPS", svg)
        self.assertIn("GEN BY COMPUTAI", svg)
        self.assertNotIn("GEN BY COMPUTAI", self.m.render_card_svg(self.card(), credit=False))

    def test_agent_ops(self):
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        rows = []
        for i in range(10):          # session a：每 60 秒一筆，9 分鐘
            rows.append(dict(source="claude", uid="a%d" % i, ts=1000 + 60 * i, model="m", session="a", output=1, requests=1))
        for i in range(4):           # session b：和 a 重疊
            rows.append(dict(source="codex", uid="b%d" % i, ts=1100 + 60 * i, model="m", session="b", output=1,
                             requests=1, subagent=1))
        rows.append(dict(source="claude", uid="a-late", ts=1000 + 60 * 9 + 3600, model="m", session="a", output=1))
        self.m.add_usage(db, rows)
        ops = self.m.card_ops(db, 0, 10 ** 6)
        self.assertEqual(ops["agent_hours"], round((540 + 180) / 3600.0, 1))   # 隔一小時那筆不算工作時間
        self.assertEqual(ops["peak_parallel"], 2)
        self.assertEqual(ops["longest_run"], 540)
        self.assertEqual((ops["prompts"], ops["subagents"]), (15, 1))
        self.assertEqual([f["source"] for f in ops["fleet"]], ["claude", "codex"])

    def test_empty_ledger(self):
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        svg = self.m.render_card_svg(self.m.card_data(db, "30d", PRICES, {}, t=self.t))
        ET.fromstring(svg)
        self.assertIn("NO USAGE YET", svg)

    def test_cli_writes_card_and_validates_period(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        out = os.path.join(sb.root, "card.svg")
        r = sb.run("--card", "--svg", out, "--card-theme", "light", "--no-sync")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as f:
            self.assertIn("#f7f7fb", f.read())
        self.assertNotEqual(sb.run("--card", "--period", "week", "--no-sync").returncode, 0)
        r = sb.run("--card", "--no-sync")                                 # 不指定檔案就印到標準輸出
        self.assertTrue(r.stdout.startswith("<svg"))


def git_env(root):
    """測試用的 git 環境：不讀使用者自己的設定（簽章、hook 等），身分固定。"""
    empty = os.path.join(root, "gitconfig")
    open(empty, "w").close()
    return dict(GIT_CONFIG_GLOBAL=empty, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class Publish(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.addCleanup(self.sb.close)
        self.env = git_env(self.sb.root)
        self.repo = os.path.join(self.sb.root, "profile")
        self.remote = os.path.join(self.sb.root, "remote.git")
        os.makedirs(self.repo)
        os.makedirs(self.remote)
        self.git("init", "-q", cwd=self.repo)
        self.git("init", "-q", "--bare", self.remote)
        self.git("remote", "add", "origin", self.remote, cwd=self.repo)
        with open(os.path.join(self.repo, "README.md"), "w") as f:
            f.write("hi\n")
        self.git("add", "README.md", cwd=self.repo)
        self.git("commit", "-q", "-m", "init", cwd=self.repo)
        self.branch = self.git("rev-parse", "--abbrev-ref", "HEAD", cwd=self.repo).stdout.strip()

    def git(self, *a, cwd=None):
        e = dict(os.environ)
        e.update(self.env)
        return subprocess.run(["git"] + list(a), cwd=cwd or self.remote, env=e, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, check=True)

    def publish(self, *extra):
        return self.sb.run("--card", "--publish", self.repo, "--no-sync", *extra, **self.env)

    def test_commits_both_cards_and_does_not_push(self):
        r = self.publish()
        self.assertEqual(r.returncode, 0, r.stderr)
        for want in ("wrote", "computai-card.svg", "computai-card-light.svg", "committed", "did not push"):
            self.assertIn(want, r.stdout)
        files = self.git("show", "--name-only", "--format=%s", "HEAD", cwd=self.repo).stdout
        self.assertIn("Update ComputAI card", files)
        self.assertIn("computai-card.svg", files)
        self.assertIn("computai-card-light.svg", files)
        self.assertEqual(self.git("rev-list", "--count", "HEAD", cwd=self.repo).stdout.strip(), "2")
        self.assertEqual(self.git("branch", "-a", cwd=self.remote).stdout.strip(), "")     # 遠端什麼都沒有
        self.assertEqual(self.git("status", "--porcelain", cwd=self.repo).stdout.strip(), "")

    def test_second_run_without_changes_makes_no_commit(self):
        self.publish()
        r = self.publish()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("nothing was committed", r.stdout)
        self.assertEqual(self.git("rev-list", "--count", "HEAD", cwd=self.repo).stdout.strip(), "2")

    def test_leaves_other_staged_files_alone(self):
        with open(os.path.join(self.repo, "other.txt"), "w") as f:
            f.write("x\n")
        self.git("add", "other.txt", cwd=self.repo)
        self.publish()
        self.assertNotIn("other.txt", self.git("show", "--name-only", "--format=", "HEAD", cwd=self.repo).stdout)
        self.assertIn("other.txt", self.git("diff", "--cached", "--name-only", cwd=self.repo).stdout)

    def test_push_only_with_flag(self):
        self.git("config", "branch.%s.remote" % self.branch, "origin", cwd=self.repo)      # 一般的個人頁 repo 都有 upstream
        self.git("config", "branch.%s.merge" % self.branch, "refs/heads/" + self.branch, cwd=self.repo)
        r = self.publish("--push")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("pushed", r.stdout)
        self.assertIn(self.branch, self.git("branch", cwd=self.remote).stdout)

    def test_push_rebases_onto_a_bot_commit(self):
        # 個人頁 repo 常有機器人推的 commit（例如自動更新文章列表）：先接上再推，不會被拒絕
        self.git("config", "branch.%s.remote" % self.branch, "origin", cwd=self.repo)
        self.git("config", "branch.%s.merge" % self.branch, "refs/heads/" + self.branch, cwd=self.repo)
        self.git("push", "-q", "origin", self.branch, cwd=self.repo)
        bot = os.path.join(self.sb.root, "bot")
        self.git("clone", "-q", self.remote, bot, cwd=self.sb.root)
        with open(os.path.join(bot, "posts.md"), "w") as f:
            f.write("new post\n")
        self.git("add", "posts.md", cwd=bot)
        self.git("commit", "-q", "-m", "bot: update posts", cwd=bot)
        self.git("push", "-q", "origin", self.branch, cwd=bot)
        r = self.publish("--push")
        self.assertEqual(r.returncode, 0, r.stderr)
        log = self.git("log", "--format=%s", self.branch, cwd=self.remote).stdout
        self.assertIn("bot: update posts", log)
        self.assertIn("Update ComputAI card", log)

    def test_errors(self):
        plain = os.path.join(self.sb.root, "plain")
        os.makedirs(plain)
        r = self.sb.run("--card", "--publish", plain, "--no-sync", **self.env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a git repository", r.stderr)
        r = self.sb.run("--card", "--publish", os.path.join(self.sb.root, "nope"), "--no-sync", **self.env)
        self.assertIn("not a folder", r.stderr)
        r = self.sb.run("--card", "--push", "--no-sync", **self.env)
        self.assertIn("--push only works", r.stderr)


class CardSetup(unittest.TestCase):
    """computai --card --setup：HOME 指到暫存資料夾，絕對碰不到使用者真的個人頁 repo。"""
    def setUp(self):
        import tempfile
        self.home = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, self.home)
        self.old = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.old)))
        cfg, data = os.path.join(self.home, "cfg"), os.path.join(self.home, "data")
        os.makedirs(cfg)
        os.environ.update(HOME=self.home, COMPUTAI_CONFIG_DIR=cfg, COMPUTAI_DATA_DIR=data, TZ="UTC")
        os.environ.update(git_env(self.home))
        self.m = helpers.load()
        self.m.set_lang("en")
        self.db = self.m.open_ledger()
        self.addCleanup(self.db.close)
        self.m.add_usage(self.db, [dict(source="claude", uid="1", ts=self.m.now() - 3600, model="claude-opus-5-5",
                                        session="s", output=1000)])
        self.db.commit()

    def wizard(self, answers):
        out = []
        answers = list(answers)
        code = self.m.Setup(self.db, ask=lambda p: answers.pop(0), out=out.append).run_card()
        self.assertEqual(answers, [], "unused answers")
        return code, "\n".join(map(str, out))

    @unittest.skipUnless(shutil.which("git"), "needs git")
    def test_finds_repo_commits_card_and_readme_without_pushing(self):
        repo = os.path.join(self.home, "Documents", "octocat")
        os.makedirs(os.path.join(repo, "assets"))
        subprocess.run(["git", "init", "-q", repo], check=True)
        subprocess.run(["git", "-C", repo, "remote", "add", "origin", "https://github.com/octocat/octocat.git"], check=True)
        with open(os.path.join(repo, "README.md"), "w") as f:
            f.write("# hi\n")
        code, text = self.wizard(["", "matrix", "n", "y", "n"])   # 接受找到的資料夾、matrix、不推、加進 README、不裝 watch
        self.assertEqual(code, 0, text)
        self.assertIn("SYS.OCTOCAT", text)
        cfg = open(os.path.join(self.home, "cfg", "config.ini")).read()
        self.assertIn("style = matrix", cfg)
        self.assertIn("push = no", cfg)
        self.assertTrue(os.path.exists(os.path.join(repo, "assets", "computai-card.svg")))
        readme = open(os.path.join(repo, "README.md")).read()
        self.assertIn('srcset="assets/computai-card-light.svg"', readme)
        log = subprocess.run(["git", "-C", repo, "log", "--format=%s"], capture_output=True, text=True).stdout
        self.assertIn("Add ComputAI card to README", log)
        self.assertIn("Update ComputAI card", log)

    def test_no_repo_and_no_gh_explains(self):
        self.m.run_cmd = lambda *a, **k: ""
        self.m.shutil.which = lambda name: None if name == "gh" else __import__("shutil").which(name)
        try:
            code, text = self.wizard([])
        finally:
            import importlib
            importlib.reload(__import__("shutil"))
        self.assertEqual(code, 1)
        self.assertIn("github.com/<you>/<you>", text)

    def test_doctor_points_to_card_setup(self):
        items = [x for x in self.m.doctor(self.db, sample=False) if x["area"] == "card"]
        self.assertEqual(items[0]["level"], "tip")
        self.assertEqual(items[0]["fix"], "computai --card --setup")
