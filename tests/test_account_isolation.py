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
