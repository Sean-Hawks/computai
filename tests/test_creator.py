import base64
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import unittest
from unittest import mock
from tests import helpers
from tests.test_wrapped import seed, PRICES, SECRET, SESSION


class Creator(unittest.TestCase):
    def setUp(self):
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
        self.assertEqual(len(payload['templates']), len(self.data['periods']) * 8)
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

    def test_create_only_imports_local_metadata_and_does_not_start_services(self):
        with mock.patch.object(self.m, 'sync') as sync, mock.patch.object(self.m, 'open_creator', return_value=('creator.html', False)) as create:
            result = self.m.run(self.m.parse_args(['--create', '--profile', '2026-09', '--no-open']), self.db)
        self.assertEqual(result, 0)
        self.assertEqual(sync.call_args.kwargs['only'], ('claude', 'codex', 'gemini', 'opencode', 'cursor'))
        self.assertEqual(create.call_args.args[3], 'month-2026-09')
        self.assertFalse(create.call_args.args[-1])
        with mock.patch.object(self.m, 'sync') as sync, mock.patch.object(self.m, 'open_creator', return_value=('creator.html', False)):
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
