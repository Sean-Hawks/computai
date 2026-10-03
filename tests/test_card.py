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
            self.assertEqual((root.get("width"), root.get("height")), ("495", "195"))
            for bad in ("<script", "<image", "href", "@font-face", "@import", "<style", "onload"):
                self.assertNotIn(bad, svg)
            self.assertEqual(svg.count("http"), 1)                        # 只有 xmlns
            for want in ("last 30 days", "13.9M", "claude-opus-5-5"):
                self.assertIn(want, svg)
            self.assertNotIn("secret", svg)
            self.assertNotIn(SESSION, svg)
        self.assertIn("#0d1117", dark)
        self.assertIn("#ffffff", light)
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

    def test_empty_ledger(self):
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        svg = self.m.render_card_svg(self.m.card_data(db, "30d", PRICES, {}, t=self.t))
        ET.fromstring(svg)
        self.assertIn("no usage yet", svg)

    def test_cli_writes_card_and_validates_period(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        out = os.path.join(sb.root, "card.svg")
        r = sb.run("--card", "--svg", out, "--card-theme", "light", "--no-sync")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as f:
            self.assertIn("#ffffff", f.read())
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
