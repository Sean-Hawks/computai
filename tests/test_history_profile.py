import json
import os
import time
import unittest
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
