import json
import os
import subprocess
import sys
import time
import unittest

from tests import helpers

T0 = 1790000000


def state(left=50.0, over=False, strict=False, ts=T0):
    return {"ts": ts, "warn_left": 10, "strict": strict, "over_budget": over, "projected": 320, "budget": 250,
            "limits": [{"label": "Claude Code weekly limit", "left": left, "resets_at": T0 + 7200}],
            "text": {"limit": "%s: %d%% left, resets in %s", "budget": "this month is heading for $%d, over the $%d budget",
                     "hint": "HINT", "strict": "STRICT"}}


class Decide(unittest.TestCase):
    """四種情況：正常、快用完、超標、帳本讀不到。"""

    def setUp(self):
        self.m = helpers.load()

    def test_normal_says_nothing(self):
        self.assertEqual(self.m.guard_decide(state(), "pretool", "Agent", T0), {})
        self.assertEqual(self.m.guard_decide(state(), "stop", None, T0), {})

    def test_running_low_reminds_without_deciding(self):
        out = self.m.guard_decide(state(left=6), "pretool", "Agent", T0)
        self.assertEqual(out["systemMessage"], "ComputAI: Claude Code weekly limit: 6% left, resets in 2h00m")
        self.assertNotIn("permissionDecision", out["hookSpecificOutput"])   # 不替使用者放行，也不擋
        self.assertIn("HINT", out["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.m.guard_decide(state(left=6), "stop", None, T0),
                         {"systemMessage": "ComputAI: Claude Code weekly limit: 6% left, resets in 2h00m"})
        self.assertEqual(self.m.guard_decide(state(left=6), "stop", None, T0 + 7300), {})   # 已經重置了

    def test_over_budget(self):
        out = self.m.guard_decide(state(over=True), "stop", None, T0)
        self.assertEqual(out["systemMessage"], "ComputAI: this month is heading for $320, over the $250 budget")

    def test_strict_only_stops_new_subagents(self):
        out = self.m.guard_decide(state(left=3, strict=True), "pretool", "Agent", T0)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("STRICT", out["hookSpecificOutput"]["permissionDecisionReason"])
        for tool in ("Task", "spawn_agent"):   # 舊版 Claude Code 和 Codex 的名字
            self.assertEqual(self.m.guard_decide(state(left=3, strict=True), "pretool", tool, T0)
                             ["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertNotIn("permissionDecision",
                         self.m.guard_decide(state(left=3, strict=True), "pretool", "Bash", T0)["hookSpecificOutput"])

    def test_unreadable_or_old_state_lets_everything_through(self):
        for st in (None, "garbage", state(left=1, ts=T0 - 3600)):
            self.assertEqual(self.m.guard_decide(st, "pretool", "Agent", T0), {})


class Shim(unittest.TestCase):
    """--setup 產生的小腳本：只讀一列、很快、出錯放行。"""

    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(self.sb.env())
        self.m = helpers.load()
        self.m.set_lang("en")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def hook(self, event, tool="Agent", stdin=None):
        t = time.time()
        r = subprocess.run([sys.executable, self.m.hook_shim_path(), event], capture_output=True, text=True,
                           input=stdin if stdin is not None else json.dumps({"hook_event_name": "x", "tool_name": tool}))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout), time.time() - t

    def test_end_to_end(self):
        path = self.m.write_hook_shim()
        self.assertEqual(self.hook("pretool")[0], {})                        # 帳本還不存在
        db = self.m.open_ledger()
        self.addCleanup(db.close)
        self.assertEqual(self.hook("stop")[0], {})                           # 帳本在，但沒有護欄狀態
        t = time.time()
        self.m.add_limits(db, [{"source": "codex", "name": "week", "ts": int(t), "used_percent": 95.0,
                                "window_minutes": 10080, "resets_at": int(t + 86400)}])
        self.m.write_guard_state(db, t)
        out, took = self.hook("pretool")
        self.assertIn("Codex weekly limit: 5% left", out["systemMessage"])
        self.assertLess(took, 1.0)                                          # 實際約 20ms；CI 機器慢，放寬
        self.assertEqual(self.hook("stop", stdin="not json")[0]["systemMessage"][:9], "ComputAI:")
        with open(path, "a") as f:                                          # 帳本路徑錯了也一樣放行
            f.write("")
        db.execute("UPDATE meta SET value = 'garbage' WHERE key = 'guard_state'")
        db.commit()
        self.assertEqual(self.hook("pretool")[0], {})

    def test_cli_fallback(self):
        r = self.sb.run("--hook", "claude-stop")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "{}"))


class Settings(unittest.TestCase):
    def test_merge_keeps_other_hooks_and_replaces_ours(self):
        m = helpers.load()
        old = {"model": "opus", "hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "my-linter"}]},
            {"matcher": "Task|Agent", "hooks": [{"type": "command", "command": "/old/claude-hook.py pretool"}]}]}}
        new = m.guard_hooks_settings(old, "/py /data/claude-hook.py")
        self.assertEqual(new["model"], "opus")
        pre = new["hooks"]["PreToolUse"]
        self.assertEqual(pre[0], old["hooks"]["PreToolUse"][0])               # 別人的 hook 原樣保留
        self.assertEqual(pre[1], {"matcher": "Task|Agent", "hooks": [
            {"type": "command", "command": "/py /data/claude-hook.py pretool", "timeout": 5}]})
        self.assertEqual(len(pre), 2)                                         # 舊的那個被換掉，不會重複
        self.assertEqual(new["hooks"]["Stop"][0]["hooks"][0]["command"], "/py /data/claude-hook.py stop")
        self.assertEqual(m.guard_hooks_settings(new, "/py /data/claude-hook.py"), new)   # 再裝一次不變


    def test_codex_hooks_json(self):
        import tempfile
        m = helpers.load()
        home = tempfile.mkdtemp()
        self.addCleanup(__import__("shutil").rmtree, home)
        old = os.environ.get("CODEX_HOME")
        os.environ["CODEX_HOME"] = home
        self.addCleanup(lambda: os.environ.pop("CODEX_HOME") if old is None else os.environ.update(CODEX_HOME=old))
        diff, new = m.guard_hooks_diff("/py /d/claude-hook.py", "codex")
        self.assertIn(os.path.join(home, "hooks.json"), diff)
        self.assertEqual(new["hooks"]["PreToolUse"][0]["matcher"], "^(spawn_agent|Agent)$")
        m.install_guard_hooks(new, "codex")
        self.assertEqual(m.guard_hooks_diff("/py /d/claude-hook.py", "codex")[0], "")   # 裝好之後沒有差異


if __name__ == "__main__":
    unittest.main()
