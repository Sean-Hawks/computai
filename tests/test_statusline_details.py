import contextlib
import io
import json
import os
import unittest
from unittest import mock
from tests import helpers


class StatuslineDetails(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        with open(helpers.fixture('statusline', 'detailed.json')) as f:
            self.payload = json.load(f)

    def test_metadata_semantics_and_privacy(self):
        with mock.patch('builtins.open', side_effect=AssertionError('must not read transcripts')):
            d = self.m.statusline_metadata(self.payload)
        self.assertEqual(d['context_input'], 15000)
        self.assertEqual(d['context_used_pct'], 7.5)
        self.assertEqual(d['last_cache_hit_pct'], 80)
        self.assertEqual(d['last_request']['output'], 1000)
        self.assertNotIn('PRIVATE', json.dumps(d))
        self.payload['context_window'].pop('used_percentage')
        self.assertEqual(self.m.statusline_metadata(self.payload)['context_used_pct'], 7.5)  # input only

    def test_null_missing_and_invalid(self):
        self.payload['context_window']['current_usage'] = None
        d = self.m.statusline_metadata(self.payload)
        self.assertIsNone(d['context_input'])
        self.assertIsNone(d['last_request']['input'])
        self.payload['model']['display_name'] = 'demo\x1b]52;bad\x07'
        self.payload['context_window']['used_percentage'] = float('nan')
        d = self.m.statusline_metadata(self.payload)
        self.assertNotIn('\x1b', d['model'])
        self.assertIsNone(d['context_used_pct'])
        self.payload['rate_limits']['five_hour']['used_percentage'] = float('inf')
        self.assertEqual(self.m.claude_statusline_limits(self.payload, 100), [])

    def test_widths_and_localized_rendering(self):
        info = {'limits': [dict(label='Claude', used_percent=42, resets_in=3600, window='5h')], 'today_usd': 1.2}
        for lang in ('en', 'zh'):
            self.m.set_lang(lang)
            for width in (40, 60, 80, 120):
                text = self.m.render_statusline(info, self.m.statusline_metadata(self.payload), width)
                self.assertTrue(all(self.m.vlen(x) <= width for x in text.splitlines()), text)
                self.assertIn('12.0k', text)
                self.assertIn('1h00m', text)
                self.assertNotIn('PRIVATE', text)

    def test_cli_json_compact_and_detail(self):
        sb = helpers.Sandbox()
        old = dict(os.environ)
        try:
            os.environ.update(sb.env(COMPUTAI_FAKE_NOW=1790000000, COLUMNS=80))
            db = self.m.open_ledger()
            for compact in (False, True):
                args = ['--statusline', '--no-sync'] + (['--statusline-view', 'compact'] if compact else [])
                out = io.StringIO()
                with mock.patch.object(self.m, 'read_statusline_stdin', return_value=self.payload), contextlib.redirect_stdout(out):
                    self.m.run(self.m.parse_args(args), db)
                self.assertEqual('Demo Model' in out.getvalue(), not compact)
            out = io.StringIO()
            with mock.patch.object(self.m, 'read_statusline_stdin', return_value=self.payload), contextlib.redirect_stdout(out):
                self.m.run(self.m.parse_args(['--statusline', '--no-sync', '--json']), db)
            self.assertEqual(json.loads(out.getvalue())['current']['context_input'], 15000)
            self.assertNotIn('PRIVATE', out.getvalue())
            self.assertEqual(db.execute('SELECT COUNT(*) FROM usage').fetchone()[0], 0)
            db.close()
        finally:
            os.environ.clear(); os.environ.update(old); sb.close()
