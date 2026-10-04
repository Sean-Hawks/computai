import os
import unittest
from unittest import mock

from tests import helpers


class AccountIsolation(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.addCleanup(self.sb.close)
        env = self.sb.env(COMPUTAI_FAKE_NOW=1790000000)
        env.pop("CLAUDE_CONFIG_DIR", None)
        env.pop("CODEX_HOME", None)
        self.env = mock.patch.dict(os.environ, env, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.m = helpers.load()
        self.db = self.m.open_ledger()
        self.addCleanup(self.db.close)

    def test_default_cli_cooldowns_are_separate(self):
        with mock.patch.object(self.m, "claude_account_limits", return_value=[]) as claude, \
                mock.patch.object(self.m, "codex_account_limits", return_value=([], None)) as codex:
            for _ in range(5):
                self.m.claude_account_poll(self.db)
                self.m.codex_account_poll(self.db)
        self.assertEqual(claude.call_count, self.m.NO_LIMITS_TRIES)
        self.assertEqual(codex.call_count, self.m.NO_LIMITS_TRIES)

    def test_successful_source_does_not_clear_another_sources_cooldown(self):
        rows = [{"source": "codex", "name": "week", "ts": 1790000000, "used_percent": 40}]
        with mock.patch.object(self.m, "claude_account_limits", return_value=[]) as claude, \
                mock.patch.object(self.m, "codex_account_limits", return_value=(rows, None)) as codex:
            for _ in range(5):
                self.m.claude_account_poll(self.db)
                self.m.codex_account_poll(self.db)
        self.assertEqual(claude.call_count, self.m.NO_LIMITS_TRIES)
        self.assertEqual(codex.call_count, 5)

    def test_statusline_does_not_borrow_another_accounts_limits(self):
        self.m.add_limits(self.db, [{"source": "claude", "account": "work", "name": "5h",
                                    "ts": 1790000000, "used_percent": 80}])
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.sb.root, ".claude-personal")
        self.assertEqual(self.m.line_parts(self.db)["limits"], [])
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.sb.root, ".claude")
        self.assertEqual(self.m.line_parts(self.db)["limits"], [])
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.sb.root, ".claude-work")
        self.assertEqual(self.m.line_parts(self.db)["limits"][0]["used_percent"], 80)

    def test_general_line_can_show_worst_of_listed_accounts(self):
        self.m.add_limits(self.db, [{"source": "codex", "account": account, "name": "week",
                                    "ts": 1790000000, "used_percent": pct}
                                   for account, pct in (("work", 80), ("personal", 20))])
        os.environ["CODEX_HOME"] = "/fake/.codex-work,/fake/.codex-personal"
        self.assertEqual(self.m.line_parts(self.db)["limits"][0]["used_percent"], 80)
