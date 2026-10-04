import base64
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import time
import unittest
from unittest import mock
from tests import helpers
from tests.test_wrapped import seed, PRICES, SECRET, SESSION


class Creator(unittest.TestCase):
    def setUp(self):
        if hasattr(time, 'tzset'):
            os.environ['TZ']='UTC';time.tzset()
        self.m = helpers.load()
        self.db = self.m.open_ledger(':memory:')
        self.addCleanup(self.db.close)
        seed(self.m, self.db)
        self.data = self.m.history_profile(self.db, self.m.calendar_ts(2026, 10, 4, 12), PRICES)

    def page(self, **kw):
        return self.m.render_creator_html(self.data, lang='zh', **kw)

    def test_page_offline_templates_escape_metadata_and_have_no_private_fields(self):
        self.data['periods'][0]['models'][0]['model'] = '</script><script>alert(1)</script>'
        page = self.page(handle='"><script>alert(2)</script>')
        self.assertNotIn(SECRET, page)
        self.assertNotIn(SESSION, page)
        self.assertNotIn('<script>alert', page)
        self.assertNotIn('src="http', page)
        self.assertNotIn('fetch(', page)
        self.assertNotIn('innerHTML', page)
        payload = json.loads(re.search(r'id="creator-data">(.*?)</script>', page, re.S)[1])
        self.assertEqual(len(payload['templates']), len(self.m.creator_history(self.data)['periods']) * 8)
        self.assertEqual(payload['templates']['month-2026-09/portrait/dark'],
                         self.m.render_mission_share_svg(self.data, 'month-2026-09', '', 'portrait', lang='zh'))
        self.assertIn('value="month-2026-09" selected', page)
        self.assertIn('勿分享此 HTML', page)
        with self.assertRaises(ValueError):
            self.page(selected='year-2025')
        self.assertIn('value="all" selected', self.page(selected='all'))

    def test_csp_hashes_match_all_inline_scripts_and_css_and_allow_no_external_requests(self):
        page = self.page()
        csp = self.m.creator_csp(page)
        self.assertIn("default-src 'none'", csp)
        self.assertNotIn('unsafe-inline', csp)
        for tag in ('script', 'style'):
            for body in re.findall(r'<%s(?:\s[^>]*)?>(.*?)</%s>' % (tag, tag), page, re.S):
                digest = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
                self.assertIn("'sha256-%s'" % digest, csp)

    def test_monthly_readiness_and_selected_export_are_aggregate_only(self):
        periods={p['key']:p for p in self.data['periods']}
        details=self.m.creator_period_details(periods['month-2026-09'],'zh')
        self.assertIn('尚無 Codex',details['guidance']['codex'])
        self.assertNotIn('尚無本地',details['guidance']['mixed'])
        self.assertIn('2026-08',details['comparisonText'])
        export=details['export']
        self.assertEqual(export['total_tokens'],12904000)
        self.assertEqual(export['period'],'2026-09')
        self.assertEqual(export['token_buckets']['reasoning'],0)
        # Neither extra metadata nor current prices / payments may enter this download.
        periods['month-2026-09']['models'][0]['project']=SECRET
        periods['month-2026-09']['coverage'][0]['session']=SESSION
        raw=json.dumps(self.m.creator_period_details(periods['month-2026-09'],'zh')['export'])
        for forbidden in (SECRET,SESSION,'cost','api_equivalent','project','session','machine','2026-08'):
            self.assertNotIn(forbidden,raw)
        self.assertIn('無紀錄的過去無法補算',self.m.creator_period_details(periods['month-2026-08'],'zh')['guidance']['local'])
        self.assertFalse(self.m.creator_period_details(dict(periods['all'],tokens=dict(periods['all']['tokens'],total=0)),'en')['hasUsage'])

    def test_missing_current_and_previous_months_are_explicit_empty_choices(self):
        original=json.dumps(self.data,sort_keys=True)
        page=self.page(selected='month-2026-10')
        payload=json.loads(re.search(r'id="creator-data">(.*?)</script>',page,re.S)[1])
        empty=next(p for p in payload['periods'] if p['key']=='month-2026-10')
        self.assertFalse(empty['hasUsage'])
        self.assertIn('尚無用量紀錄',empty['caption'])
        self.assertNotIn('0 token',empty['caption'])
        self.assertEqual(json.dumps(self.data,sort_keys=True),original)
        # A newer history start must not reverse the missing previous month's dates.
        db=self.m.open_ledger(':memory:')
        try:
            at=self.m.calendar_ts(2026,1,4,12)
            self.m.add_usage(db,[dict(source='codex',uid='jan',ts=at-1,output=5)])
            d=self.m.history_profile(db,at,{})
            creator=self.m.creator_history(d)
            prev=next(p for p in creator['periods'] if p['key']=='month-2025-12')
            self.assertFalse(self.m.creator_period_details(prev,'zh')['hasUsage'])
            page=self.m.render_creator_html(d,selected='month-2025-12',lang='zh')
            payload=json.loads(re.search(r'id="creator-data">(.*?)</script>',page,re.S)[1])
            text=next(p['caption'] for p in payload['periods'] if p['key']=='month-2025-12')
            self.assertIn('2025-12-01 ~ 2025-12-31',text)
        finally:db.close()

    def test_create_only_imports_local_metadata_and_does_not_start_services(self):
        with mock.patch('sys.stdout'), mock.patch.object(self.m, 'sync') as sync, mock.patch.object(self.m, 'open_creator', return_value=('creator.html', False)) as create:
            result = self.m.run(self.m.parse_args(['--create', '--profile', '2026-09', '--no-open']), self.db)
        self.assertEqual(result, 0)
        self.assertEqual(sync.call_args.kwargs['only'], ('claude', 'codex', 'gemini', 'opencode', 'cursor'))
        self.assertEqual(create.call_args.args[3], 'month-2026-09')
        self.assertFalse(create.call_args.args[-1])
        with mock.patch('sys.stdout'), mock.patch.object(self.m, 'sync') as sync, mock.patch.object(self.m, 'open_creator', return_value=('creator.html', False)):
            self.m.run(self.m.parse_args(['--create', '--no-sync', '--no-open']), self.db)
        sync.assert_not_called()

    def test_cli_writes_private_page_without_opening_browser_or_running_setup(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        result = sb.run('--create', '--no-open', '--no-sync', '--lang', 'zh')
        self.assertEqual(result.returncode, 0, result.stderr)
        path = os.path.join(sb.data, 'creator.html')
        with open(path, encoding='utf-8') as f:
            page = f.read()
        self.assertIn('目前找不到本機用量', page)
        self.assertIn('"hasUsage": false', page)
        self.assertIn('value="all" selected', page)
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertNotIn('setup', result.stdout)
        self.assertFalse(os.path.exists(os.path.join(sb.data, 'watch.pid')))

    def test_open_creator_uses_file_uri_and_atomic_600_even_when_replacing_public_file(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        path = os.path.join(sb.root, 'my card.html')
        with open(path, 'w') as f:
            f.write('previous')
        os.chmod(path, 0o644)
        with mock.patch('webbrowser.open', return_value=True) as browser:
            result, opened = self.m.open_creator(self.db, path, selected='month-2026-09', lang='zh')
        self.assertEqual(result, path)
        self.assertTrue(opened)
        self.assertIn('my%20card.html', browser.call_args.args[0])
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertFalse(any(p.endswith('.tmp') for p in os.listdir(sb.root)))

    @unittest.skipUnless(shutil.which('node'), 'optional JS behavior checks')
    def test_creator_controls_downloads_and_copy_feedback(self):
        result = subprocess.run(['node', os.path.join(helpers.ROOT, 'tests', 'creator_dom.js')],
                                input=self.page(), text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_existing_ledger_is_read_only_and_missing_ledger_stays_in_memory(self):
        import sqlite3
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        with mock.patch.dict(os.environ, sb.env()):
            db = self.m.creator_ledger()
            db.close()
            self.assertFalse(os.path.exists(self.m.ledger_path()))
            db = self.m.open_ledger()
            seed(self.m, db)
            db.commit()
            db.close()
            db = self.m.creator_ledger()
            try:
                self.assertEqual(self.m.history_profile(db)['periods'][0]['tokens']['total'], 13904000)
                with self.assertRaises(sqlite3.OperationalError):
                    db.execute('DELETE FROM usage')
            finally:
                db.close()

    def test_tui_c_opens_creator_without_sync_and_restores_terminal(self):
        import io
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        out = io.StringIO()
        with mock.patch.dict(os.environ, sb.env()), mock.patch.object(self.m.threading, 'Thread'), \
                mock.patch.object(self.m, 'read_key', side_effect=['c', 'q']), \
                mock.patch.object(self.m, 'open_creator', return_value=('creator.html', True)) as creator, \
                mock.patch.object(self.m, 'sync') as sync, mock.patch('sys.stdout', out), \
                mock.patch('sys.stdin') as stdin:
            stdin.isatty.return_value = False
            self.assertEqual(self.m.run_live(1, 0, intro=False), 0)
        creator.assert_called_once()
        sync.assert_not_called()
        self.assertIn('Card creator opened', out.getvalue())
        self.assertIn('\x1b[?1049l', out.getvalue())


class CreatorWeb(unittest.TestCase):
    def setUp(self):
        import http.server
        import threading
        self.m = helpers.load()
        self.sb = helpers.Sandbox()
        self.addCleanup(self.sb.close)
        self.env = mock.patch.dict(os.environ, self.sb.env())
        self.env.start()
        self.addCleanup(self.env.stop)
        db = self.m.open_ledger()
        seed(self.m, db)
        db.commit()
        db.close()
        self.state = {'lock': threading.Lock(), 'state': {'lang': 'zh'}, 'metrics': None}
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), self.m.web_handler(self.state, '127.0.0.1', 5))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path, host=None):
        import http.client
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        conn.request('GET', path, headers={'Host': host or 'localhost'})
        response = conn.getresponse()
        body = response.read().decode()
        conn.close()
        return response, body

    def test_web_creator_is_private_read_only_and_keeps_existing_csp_and_host_guards(self):
        with mock.patch.object(self.m, 'sync') as sync:
            response, page = self.get('/create')
        sync.assert_not_called()
        self.assertEqual(response.status, 200)
        self.assertIn('做我的圖卡', page)
        self.assertNotIn(SECRET, page)
        self.assertNotIn(SESSION, page)
        self.assertEqual(response.getheader('Cache-Control'), 'no-store')
        self.assertEqual(response.getheader('Content-Security-Policy'), self.m.creator_csp(page))
        self.assertNotIn('unsafe-inline', response.getheader('Content-Security-Policy'))
        r, main = self.get('/')
        self.assertIn('href="/create"', main)
        self.assertIn("default-src 'self'", r.getheader('Content-Security-Policy'))
        with mock.patch.object(self.m, 'creator_ledger') as ledger:
            self.assertEqual(self.get('/create', 'evil.example')[0].status, 403)
            ledger.assert_not_called()
