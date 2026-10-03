import json
import os
import shutil
import subprocess
import unittest

from tests import helpers

T0 = 1790000000


def git(*a, cwd=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@example.com")
    return subprocess.run(["git"] + list(a), cwd=cwd, env=env, check=True, capture_output=True, text=True)


@unittest.skipUnless(shutil.which("git"), "needs git")
class Team(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(self.sb.env(COMPUTAI_FAKE_NOW=str(T0), GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
                                      GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com"))
        root = self.sb.root
        self.remote = os.path.join(root, "remote.git")
        git("init", "-q", "--bare", "-b", "main", self.remote)
        self.repo = os.path.join(root, "team")
        git("clone", "-q", self.remote, self.repo)
        git("commit", "-q", "--allow-empty", "-m", "start", cwd=self.repo)
        git("push", "-q", "-u", "origin", "HEAD:main", cwd=self.repo)
        os.makedirs(self.sb.config)
        with open(os.path.join(self.sb.config, "config.ini"), "w") as f:
            f.write("[team]\nrepo = %s\nhandle = neo\n[machines]\nsecret-box = 10.1.2.3\n" % self.repo)
        self.m = helpers.load()
        self.m.set_lang("en")
        self.db = self.m.open_ledger()
        day = 86400
        self.m.add_usage(self.db, [
            {"source": "claude", "uid": "a%d" % i, "ts": T0 - i * day - 600, "session": "sess-secret",
             "project": "/Users/neo/top-secret-project", "model": "claude-opus-5-5", "output": 1000, "input": 50}
            for i in range(3)] + [
            {"source": "codex", "uid": "b", "ts": T0 - 9 * day, "project": "/srv/other-secret", "model": "gpt-5.5",
             "output": 500, "device": "dev-laptop-secret"},
            {"source": "local", "uid": "c", "ts": T0 - 3600, "project": "secret-box", "model": "qwen3:8b", "output": 7}])
        self.m.note_device(self.db, "dev-laptop-secret", name="laptop-secret", seen=T0)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def test_payload_has_only_totals(self):
        p = self.m.team_payload(self.db, "neo")
        self.assertEqual(set(p), {"computai_team", "handle", "updated", "week", "prev_week"})
        self.assertEqual(set(p["week"]), {"tokens", "agent_hours", "max_concurrent", "streak_days"})
        self.assertEqual(p["week"]["streak_days"], 3)
        self.assertEqual(p["week"]["tokens"], 3 * 1050 + 7)
        text = json.dumps(p)
        for leak in ("secret", "/Users", "/srv", "10.1.2.3", "sess-", "qwen", "claude-opus", "laptop", "neo/"):
            self.assertNotIn(leak, text)

    def test_publish_show_and_leave(self):
        said = []
        self.assertEqual(self.m.team_publish(self.db, ask=lambda q: "y", out=said.append), 0)
        self.assertIn('"tokens": 3157', "\n".join(said))                      # 發佈前先顯示完整 JSON
        # 隊友：另一個 clone 讀得到；也放一個不合格式的檔案，會被略過
        other = os.path.join(self.sb.root, "other")
        git("clone", "-q", self.remote, other)
        self.assertTrue(os.path.exists(os.path.join(other, "computai-team-neo.json")))
        with open(os.path.join(other, "computai-team-trinity.json"), "w") as f:
            json.dump({"computai_team": 1, "handle": "trinity", "updated": T0,
                       "week": {"tokens": 99999, "agent_hours": 2, "max_concurrent": 3, "streak_days": 1, "project": "x"},
                       "prev_week": {"tokens": 50000}}, f)
        with open(os.path.join(other, "computai-team-evil.json"), "w") as f:
            f.write('{"computai_team": 1, "handle": "../../etc"}')
        rows = self.m.team_board(other, "neo")
        self.assertEqual([r["handle"] for r in rows], ["trinity", "neo"])
        self.assertEqual(rows[0]["change"], 100)
        self.assertNotIn("project", rows[0]["week"])
        text = self.m.render_team(rows, T0)
        self.assertIn("neo *", text)
        # 撤回：檔案從遠端消失
        self.assertEqual(self.m.team_leave(ask=lambda q: "y", out=said.append), 0)
        git("pull", "-q", cwd=other)
        self.assertFalse(os.path.exists(os.path.join(other, "computai-team-neo.json")))

    def test_saying_no_publishes_nothing(self):
        self.assertEqual(self.m.team_publish(self.db, ask=lambda q: "n", out=lambda s: None), 1)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "computai-team-neo.json")))
        r = self.sb.run("--team", "publish", "--no-sync")                     # 沒有終端機又沒有 --yes：拒絕
        self.assertIn("--yes", r.stderr)


if __name__ == "__main__":
    unittest.main()
