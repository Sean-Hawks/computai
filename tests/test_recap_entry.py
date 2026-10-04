import io
import json
import os
import re
import stat
import unittest
from unittest import mock

from tests import helpers
from tests.test_wrapped import PRICES, SECRET, SESSION, seed


class RecapEntry(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.addCleanup(self.sb.close)
        self.m = helpers.load()
        self.at = self.m.calendar_ts(2026, 10, 4, 12)

    def seeded_ledger(self):
        with mock.patch.dict(os.environ, self.sb.env()):
            db = self.m.open_ledger()
            seed(self.m, db)
            db.commit()
            db.close()

    def test_plain_command_selects_and_explains_same_month_as_page(self):
        self.seeded_ledger()
        result = self.sb.run('recap', '--no-open', '--no-sync', '--lang', 'zh', COMPUTAI_FAKE_NOW=self.at)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('已選範圍：2026-09', result.stdout)
        self.assertIn('12,904,000', result.stdout)
        self.assertIn('下載 PNG', result.stdout)
        for forbidden in (SECRET, SESSION, '--profile', '--setup', 'API equivalent'):
            self.assertNotIn(forbidden, result.stdout)
        path = os.path.join(self.sb.data, 'creator.html')
        with open(path, encoding='utf-8') as f:
            page = f.read()
        self.assertIn('value="month-2026-09" selected', page)
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_explicit_month_uses_same_local_metadata_import_as_creator(self):
        db = self.m.open_ledger(':memory:')
        self.addCleanup(db.close)
        seed(self.m, db)
        args = self.m.parse_args(['recap', '2026-08', '--lang', 'zh'])
        with mock.patch.object(self.m, 'sync') as sync, mock.patch.object(self.m, 'now', return_value=self.at), \
                mock.patch.object(self.m, 'open_creator', return_value=('saved.html', True)) as create, \
                mock.patch('sys.stdout', new_callable=io.StringIO) as stdout:
            self.assertEqual(self.m.run(args, db), 0)
        self.assertEqual(sync.call_args.kwargs['only'], ('claude', 'codex', 'gemini', 'opencode', 'cursor'))
        self.assertEqual(create.call_args.args[3], 'month-2026-08')
        self.assertTrue(create.call_args.args[5])
        self.assertIn('2026-08', stdout.getvalue())
        self.assertEqual(create.call_args.kwargs['profile_data']['periods'][0]['tokens']['total'], 13904000)

    def test_first_run_skips_plan_setup_updates_and_browser_when_no_open(self):
        output = io.StringIO()
        with mock.patch.dict(os.environ, self.sb.env()), mock.patch('sys.stdout', output), \
                mock.patch('sys.stderr.isatty', return_value=True), \
                mock.patch.object(self.m, 'ask_plans_once') as plans, \
                mock.patch.object(self.m, 'check_update_in_background') as updates, \
                mock.patch('webbrowser.open') as browser:
            self.assertEqual(self.m.main(['recap', '--no-open', '--no-sync', '--lang', 'zh']), 0)
        plans.assert_not_called()
        updates.assert_not_called()
        browser.assert_not_called()
        self.assertIn('尚無可見用量', output.getvalue())
        self.assertIn('不能補算', output.getvalue())
        self.assertNotIn('已記錄 0 token', output.getvalue())

    def test_focused_help_and_bad_inputs_have_no_side_effects(self):
        result = self.sb.run('recap', '--help')
        self.assertEqual(result.returncode, 0)
        self.assertIn('computai recap 2026-09', result.stdout)
        self.assertLess(len(result.stdout.splitlines()), 28)
        self.assertNotIn('--proxy', result.stdout)
        self.assertNotIn('--card-style', result.stdout)
        for args in (['2026-13'], ['2026-1'], ['2026-02-01'], ['--bench'], ['--summary'], ['--no-op']):
            result = self.sb.run('recap', *args)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertNotIn('Traceback', result.stderr)
        self.assertFalse(os.path.exists(self.sb.config))
        self.assertFalse(os.path.exists(self.sb.data))

    def test_missing_recorded_month_has_recovery_and_current_empty_month_is_visible(self):
        self.seeded_ledger()
        result = self.sb.run('recap', '2025-01', '--no-sync', '--no-open', '--lang', 'zh', COMPUTAI_FAKE_NOW=self.at)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('執行 computai recap', result.stderr)
        result = self.sb.run('recap', '2026-10', '--no-sync', '--no-open', '--lang', 'zh', COMPUTAI_FAKE_NOW=self.at)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('尚無可見用量', result.stdout)
        with open(os.path.join(self.sb.data, 'creator.html'), encoding='utf-8') as f:
            page = f.read()
        self.assertIn('value="month-2026-10" selected', page)
        payload = json.loads(re.search(r'id="creator-data">(.*?)</script>', page, re.S)[1])
        self.assertFalse(next(p for p in payload['periods'] if p['key'] == 'month-2026-10')['hasUsage'])

    def test_legacy_annual_recap_and_creator_keep_their_meaning(self):
        annual = self.m.parse_args(['--recap', '2026'])
        self.assertEqual(annual.recap, 2026)
        self.assertFalse(annual.create)
        self.assertFalse(annual.recap_entry)
        legacy = self.m.parse_args(['--create', '--profile', '2026'])
        self.assertTrue(legacy.create)
        self.assertFalse(legacy.recap_entry)
