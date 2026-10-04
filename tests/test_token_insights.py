import json
import os
import unittest
from tests import helpers


class TokenInsights(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.db = self.m.open_ledger(':memory:')
        self.m.add_usage(self.db, [dict(source='claude', uid='a', ts=100, model='demo', project='fake-project',
                                      input=10, cache_read=70, cache_write_5m=5, cache_write_1h=5, output=10, reasoning=4),
                                   dict(source='local', uid='b', ts=101, model='demo-local', project='fake-machine', input=5, output=5),
                                   dict(source='cloud', uid='c', ts=101, input=900),
                                   dict(source='claude', uid='outside', ts=200, input=999)])

    def tearDown(self):
        self.db.close()

    def test_totals_and_distinct_denominators(self):
        d = self.m.token_insights(self.db, 100, 200)
        self.assertEqual(d['total'], 110)
        self.assertEqual(d['buckets']['reasoning'], 4)
        self.assertEqual(d['cache_share_pct'], 63.64)
        self.assertEqual(d['cache_hit_pct'], 73.68)
        self.assertEqual(d['models'][0], {'name': 'demo', 'tokens': 100})
        self.assertEqual(sum(x['tokens'] for x in d['sources']), 110)
        public = self.m.token_insights(self.db, 100, 200, rankings=False)
        self.assertNotIn('fake-project', json.dumps(public))
        self.assertNotIn('projects', public)

    def test_empty_and_explanation(self):
        d = self.m.token_insights(self.db, 0, 1)
        self.assertIsNone(d['cache_share_pct'])
        self.assertIsNone(d['cache_hit_pct'])
        self.m.set_lang('zh')
        text = self.m.render_token_insights(self.m.token_insights(self.db, 100, 200))
        self.assertIn('已含於輸出', text)
        self.assertIn('十億', text)

    def test_card_details_share_the_card_range_and_hide_projects(self):
        import xml.etree.ElementTree as ET
        c = self.m.card_data(self.db, 'all', prices={}, plan_table={}, t=150)
        self.assertEqual(c['tokens'], c['token_details']['total'])
        self.assertNotIn('fake-project', json.dumps(c['token_details']))
        for layout in ('hud', 'compact', 'dashboard', 'portrait'):
            svg = self.m.render_card_svg(c, lang='zh', layout=layout)
            ET.fromstring(svg)
            self.assertIn('快取讀取占總數', svg)
            self.assertIn('推理（已含於輸出）', svg)
            self.assertNotIn('fake-project', svg)

    def test_cli_range_and_json(self):
        sb = helpers.Sandbox()
        try:
            os.makedirs(sb.data)
            db = self.m.open_ledger(os.path.join(sb.data, 'ledger.sqlite'))
            self.m.add_usage(db, [dict(source='claude', uid='demo', ts=self.m.parse_day('2026-09-15'), input=10)])
            db.commit(); db.close()
            r = sb.run('--tokens', '--no-sync', '--json', COMPUTAI_FAKE_NOW=1791072000)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout)['total'], 10)
            r = sb.run('--tokens', '--no-sync', '--month', '2026-10', '--json')
            self.assertEqual(json.loads(r.stdout)['total'], 0)
        finally:
            sb.close()
