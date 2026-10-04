import contextlib
import io
import json
import unittest
from unittest import mock
from tests import helpers


class LocalRequests(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.db = self.m.open_ledger(':memory:')
        self.addCleanup(self.db.close)
        rows = [('one', 100, 'box', 'demo', '/api/chat', 'test', 200, 'ok', 2.0, 30, 10, 0),
                ('two', 101, 'box', 'demo', '/api/chat', 'production', 502, 'upstream_error', 1.0, None, None, 0),
                ('other', 99, 'other', '<fake>\x1b[31m', '/api/chat', None, 200, 'usage_missing', 0.0, None, None, 0)]
        self.db.executemany('INSERT INTO proxy_requests VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', rows)

    def test_reader_filters_speed_and_unknown(self):
        d = self.m.local_requests(self.db, 100, 102)
        self.assertEqual(len(d['rows']), 2)
        self.assertIsNone(d['rows'][0]['output_tok_s'])
        self.assertIsNone(d['rows'][0]['input'])
        self.assertEqual(d['rows'][1]['output_tok_s'], 5.0)
        d = self.m.local_requests(self.db, 0, 200, machine='box', model='demo', tag='test', limit=1)
        self.assertEqual(d['rows'][0]['http_status'], 200)
        self.assertEqual(len(d['rows']), 1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM usage').fetchone()[0], 0)
        with self.assertRaises(ValueError):
            self.m.local_requests(self.db, limit=201)

    def test_render_is_localized_bounded_and_sanitized(self):
        d = self.m.local_requests(self.db, 0, 200)
        for lang in ('zh', 'en'):
            self.m.set_lang(lang)
            for width in (40, 60, 80, 145):
                for height in (None, 15, 20):
                    lines = self.m.render_local_requests(d, width, height)
                    self.assertTrue(all(self.m.vlen(x) <= width for x in lines))
                    if height:
                        self.assertLessEqual(len(lines), height)
                    self.assertNotIn('\x1b', '\n'.join(lines))
            text = '\n'.join(self.m.render_local_requests(d, 145))
            self.assertIn('5.0 tok/s', text)
            self.assertIn('?/?', text)
            self.assertIn('test', text)

    def test_cli_is_read_only_and_empty_is_helpful(self):
        args = self.m.parse_args(['--local-requests', '3', '--since', '1970-01-01', '--until', '1970-01-01', '--json', '--tag', 'test'])
        out = io.StringIO()
        with mock.patch.object(self.m, 'sync', side_effect=AssertionError('must not sync')), contextlib.redirect_stdout(out):
            self.m.run(args, self.db)
        d = json.loads(out.getvalue())
        self.assertEqual(d['rows'][0]['output_tok_s'], 5.0)
        self.assertNotIn('uid', d['rows'][0])
        self.m.set_lang('zh')
        self.assertIn('新版 proxy', '\n'.join(self.m.render_local_requests({'rows': []})))

    def test_old_usage_does_not_invent_request_metadata(self):
        self.m.add_usage(self.db, [dict(source='local', uid='legacy', ts=200, session='proxy', input=10, output=20)])
        self.assertEqual(self.m.local_requests(self.db, 200, 201)['rows'], [])
