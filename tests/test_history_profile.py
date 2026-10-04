import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest import mock
from tests import helpers
from tests.test_wrapped import PRICES, SECRET, SESSION, seed


class HistoryProfile(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.db = self.m.open_ledger(':memory:')
        self.addCleanup(self.db.close)
        if hasattr(time, 'tzset'):
            os.environ['TZ']='UTC';time.tzset()
        seed(self.m, self.db)
        self.t=self.m.calendar_ts(2026,10,4,12)
        self.m.add_usage(self.db,[dict(source='claude',uid='future',ts=self.t+3600,input=999999999),
            dict(source='cloud',uid='gpu',ts=self.t-10,cost_usd=500,input=900000000)])

    def test_observed_calendar_periods_and_subsets(self):
        d=self.m.history_profile(self.db,self.t,PRICES)
        self.assertEqual([p['key'] for p in d['periods']],['all','year-2026','month-2026-09','month-2026-08'])
        totals={p['key']:p['tokens']['total'] for p in d['periods']}
        self.assertEqual(totals['all'],totals['month-2026-09']+totals['month-2026-08'])
        self.assertEqual(totals['all'],totals['year-2026'])
        self.assertTrue(d['periods'][1]['in_progress'])
        self.assertTrue(d['periods'][1]['history_starts_late'])
        self.assertEqual(d['periods'][1]['active_days'],6)
        self.assertEqual(d['periods'][2]['active_days'],5)
        self.assertNotIn(SECRET,json.dumps(d))
        self.assertNotIn(SESSION,json.dumps(d))
        self.assertNotIn('project',json.dumps(d))
        self.assertNotIn('cloud',json.dumps(d))

    def test_local_usage_and_reasoning_do_not_fake_cost_or_activity(self):
        db=self.m.open_ledger(':memory:')
        try:
            self.m.add_usage(db,[dict(source='local',uid='x',ts=self.t-10,model='unknown',output=50,reasoning=10,cost_usd=0)])
            p=self.m.history_profile(db,self.t,PRICES)['periods'][0]
            self.assertEqual((p['tokens']['total'],p['active_days'],p['longest_streak']),(50,1,1))
            self.assertEqual(p['unpriced_models'],['unknown'])
            self.assertEqual(p['api_equivalent_usd'],0)
        finally:db.close()

    def test_empty_profile(self):
        db=self.m.open_ledger(':memory:')
        try:
            d=self.m.history_profile(db,self.t,{})
            self.assertIsNone(d['coverage']['first'])
            self.assertEqual(len(d['periods']),1)
            self.assertEqual(d['periods'][0]['tokens']['total'],0)
        finally:db.close()

    def test_profile_html_is_local_private_and_escapes_metadata(self):
        attack='</script><img src=x onerror=alert(1)>'
        self.m.add_usage(self.db,[dict(source='local',uid='html',ts=self.t-10,model=attack,output=7)])
        d=self.m.history_profile(self.db,self.t,PRICES)
        page=self.m.render_history_profile_html(d,attack,lang='zh')
        self.assertIn('<html lang="zh-Hant">',page)
        self.assertIn('2026 年報',page)
        self.assertIn('2026-09 月報',page)
        self.assertIn('快取讀取占總數',page)
        self.assertIn('不是帳單',page)
        self.assertIn('較早日期沒有資料',page)
        self.assertNotIn(SECRET,page)
        self.assertNotIn(SESSION,page)
        self.assertNotIn(attack,page)
        self.assertIn('&lt;/script&gt;',page)
        self.assertEqual(page.count('<script>'),1)
        self.assertEqual(page.count('</script>'),1)
        self.assertNotRegex(page,r'<(?:script|img|link)[^>]+(?:src|href)=')
        self.assertIn('<noscript>',page)
        self.assertNotRegex(page,r'<section[^>]+\bhidden\b')

    def test_calendar_spacing_does_not_compress_missing_days(self):
        d=self.m.history_profile(self.db,self.t,PRICES)
        page=self.m.render_history_profile_html(d,selected='month-2026-09',lang='en')
        section=page.split('id="month-2026-09"',1)[1].split('</section>',1)[0]
        positions=[float(x) for x in re.findall(r'<rect class="bar" x="([\d.]+)"',section)]
        self.assertEqual(len(positions),5)
        self.assertAlmostEqual(positions[1]-positions[0],994/30,places=1)
        self.assertAlmostEqual(positions[4]-positions[3],6*994/30,places=1)
        self.assertIn('value="month-2026-09" data-kind="month" selected',page)
        self.assertIn('2026 monthly report',page.replace('2026-09','2026'))

    @unittest.skipUnless(shutil.which('node'),'Node is optional for HTML interaction checks')
    def test_report_switching_hash_theme_and_print(self):
        d=self.m.history_profile(self.db,self.t,PRICES)
        page=self.m.render_history_profile_html(d,selected='month-2026-09',lang='zh')
        result=subprocess.run(['node',os.path.join(helpers.ROOT,'tests','profile_dom.js')],
                              input=page,text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_profile_cli_only_syncs_metadata_sources(self):
        called=[]
        def reader(name):
            def fn(db):
                called.append(name)
                return 0
            return fn
        names=('claude','codex','gemini','opencode','cursor','devices','anthropic-api','openai-api')
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(self.m,'SOURCES',[(n,reader(n)) for n in names]), \
                mock.patch.object(self.m,'write_guard_state'), mock.patch.object(self.m,'now',return_value=self.t), \
                mock.patch('sys.stdout'):
            path=os.path.join(tmp,'profile.html')
            self.m.run(self.m.parse_args(['--profile','2026','--html',path,'--who','Demo','--lang','zh']),self.db)
            with open(path,encoding='utf-8') as f:page=f.read()
            self.assertEqual(called,list(names[:5]))
            self.assertIn('Demo · AI 用量檔案',page)
            self.assertIn('value="year-2026" data-kind="year" selected',page)
            called.clear()
            self.m.run(self.m.parse_args(['--profile','--html',path,'--no-sync']),self.db)
            self.assertEqual(called,[])
        with mock.patch.object(self.m,'now',return_value=self.t):
            with self.assertRaisesRegex(SystemExit,'no observed usage'):
                self.m.run(self.m.parse_args(['--profile','2025','--no-sync']),self.db)

    def test_cli_exports_aggregate_json_and_handles_empty_html(self):
        box=helpers.Sandbox()
        self.addCleanup(box.close)
        result=box.run('--profile','--json','--no-sync')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['periods'][0]['tokens']['total'],0)
        path=os.path.join(box.root,'empty.html')
        result=box.run('--profile','--html',path,'--lang','zh','--no-sync')
        self.assertEqual(result.returncode,0,result.stderr)
        with open(path,encoding='utf-8') as f:page=f.read()
        self.assertIn('目前沒有可見紀錄',page)

    def test_cache_writes_reasoning_year_boundaries_and_price_estimates(self):
        db=self.m.open_ledger(':memory:')
        try:
            rows=[dict(source='claude',uid='end',ts=self.m.calendar_ts(2025,12,31,23),model='claude-opus-5-5',
                       input=10,cache_read=20,cache_write_5m=30,cache_write_1h=40,output=50,reasoning=15,cost_usd=999),
                  dict(source='codex',uid='start',ts=self.m.calendar_ts(2026,1,1,0),output=10)]
            self.m.add_usage(db,rows)
            d=self.m.history_profile(db,self.t,PRICES)
            periods={p['key']:p for p in d['periods']}
            self.assertEqual(periods['all']['tokens']['total'],160)
            self.assertEqual(periods['year-2025']['tokens']['total'],150)
            self.assertFalse(periods['year-2025']['in_progress'])
            self.assertEqual(periods['year-2026']['tokens']['total'],10)
            self.assertEqual(periods['month-2025-12']['tokens']['buckets']['reasoning'],15)
            self.assertLess(periods['all']['api_equivalent_usd'],1)
        finally:db.close()
