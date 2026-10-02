import os
import unittest

from tests import helpers

PRICES = {"claude-opus-5-5": {"input": 4.0, "output": 20.0, "cache_read": 0.2,
                              "cache_write_5m": 5.0, "cache_write_1h": 8.0}}


class CacheReport(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)

    def req(self, uid, ts, read, w1h, session="s1", sub=0):
        return dict(source="claude", uid=uid, ts=ts, model="claude-opus-5-5", session=session,
                    project="/p/demo", input=10, cache_read=read, cache_write_1h=w1h, output=100, subagent=sub)

    def test_rewrites_and_waste(self):
        self.m.add_usage(self.db, [
            self.req("1", 1000, 0, 100000),          # 第一筆：寫入快取是正常的
            self.req("2", 1060, 100000, 2000),       # 命中
            self.req("3", 1060 + 4000, 0, 102000),   # 隔了 4000 秒 > 1 小時：過期重寫
            self.req("4", 5100, 102000, 1000),
            self.req("5", 5200, 0, 103000),          # 沒隔多久卻整段重寫：前綴變了
            self.req("6", 5300, 0, 50000, sub=1),    # subagent 不算
            self.req("7", 5300, 0, 50000, session="s2"),   # 別的 session 的第一筆
        ])
        c = self.m.cache_report(self.db, 0, 10000, PRICES)
        self.assertEqual((c["rewrites"], c["expired"]), (2, 1))
        self.assertAlmostEqual(c["wasted_usd"], round((102000 + 103000) * (8.0 - 0.2) / 1e6, 2))
        s = c["sessions"][0]
        self.assertEqual((s["session"], s["requests"], s["rewrites"]), ("s1", 5, 2))
        text = self.m.render_cache(c)
        self.assertIn("2 rewrites (1 after idle expiry)", text)
        self.assertIn("p/demo", text)


if __name__ == "__main__":
    unittest.main()


class Forecast(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        os.makedirs(self.sb.config)
        with open(os.path.join(self.sb.config, "config.ini"), "w") as f:
            f.write("[plans]\nclaude = Max, 100, x\ncodex = Plus, 20, x\n\n[budget]\nmonthly_usd = 200\n")
        self.old = dict(os.environ)
        os.environ.update(COMPUTAI_CONFIG_DIR=self.sb.config, TZ="UTC")
        if hasattr(__import__("time"), "tzset"):
            __import__("time").tzset()
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def test_projection(self):
        t = self.m.calendar_ts(2026, 9, 11)            # 9/11 00:00，過了 10 天、還剩 20 天
        self.m.add_usage(self.db, [
            dict(source="cloud", uid="a", ts=self.m.calendar_ts(2026, 9, 2), model="H100", cost_usd=30.0),
            dict(source="cloud", uid="b", ts=self.m.calendar_ts(2026, 9, 8), model="H100", cost_usd=14.0),
            dict(source="claude", uid="c", ts=self.m.calendar_ts(2026, 9, 5), model="claude-opus-5-5",
                 output=1000000),
        ])
        f = self.m.forecast(self.db, t=t)
        self.assertEqual(f["subscriptions_usd"], 120.0)
        self.assertEqual(f["variable_so_far_usd"], 44.0)
        self.assertEqual(f["daily_rate_usd"], 2.0)           # 最近 7 天花了 14
        self.assertEqual(f["projected_usd"], 120 + 44 + 2 * 20)
        self.assertTrue(f["over_budget"])
        self.assertEqual(f["subscription_value_projected"]["claude"], 60.0)   # $20 花了 10 天 -> 30 天 $60
        self.assertIn("! over the $200.00 budget", self.m.render_forecast(f))


class Plans(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        os.makedirs(self.sb.config)
        with open(os.path.join(self.sb.config, "config.ini"), "w") as f:
            f.write("[plans]\nclaude = Max 20x, 200, x\ncodex = Plus, 20, x\n\n"
                    "[plan_options]\nclaude = Pro 20 x1, Max 5x 100 x5, Max 20x 200 x20\n"
                    "codex = Plus 20 x1, Pro 200 x20\n")
        self.old = dict(os.environ)
        os.environ["COMPUTAI_CONFIG_DIR"] = self.sb.config
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def test_downgrade_and_upgrade(self):
        t = 10 * 86400
        lim = lambda src, ts, pct: dict(source=src, name="week", ts=ts, used_percent=pct, window_minutes=10080)
        self.m.add_limits(self.db, [lim("claude", t - 86400, 12.0), lim("claude", t - 3600, 15.0),
                                    lim("codex", t - 3600, 100.0)])
        sims = {r["source"]: r for r in self.m.simulate_plans(self.db, t=t)}
        c = sims["claude"]
        self.assertEqual(c["peak_percent"], 15.0)
        # 15% 的 20x -> 5x 約 60%、Pro 約 300%
        self.assertEqual(c["recommend"], "Max 5x")
        self.assertEqual([o["projected_peak"] for o in c["options"]], [300.0, 60.0, 15.0])
        self.assertEqual(sims["codex"]["recommend"], "Pro")
        text = self.m.render_plans(self.m.simulate_plans(self.db, t=t))
        self.assertIn("-> consider Max 5x: peak was only 15% of the week limit", text)
        self.assertIn("-> consider Pro: you reached 100% of the week limit", text)

    def test_api_cheaper(self):
        self.m.add_usage(self.db, [dict(source="claude", uid="1", ts=100, model="claude-opus-5-5", output=100000)])
        c = [r for r in self.m.simulate_plans(self.db, t=200) if r["source"] == "claude"][0]
        self.assertTrue(c["api_cheaper"])
        self.assertIn("no limit data yet", c["reason"])


class Payback(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        os.makedirs(self.sb.config)
        self.old = dict(os.environ)
        os.environ["COMPUTAI_CONFIG_DIR"] = self.sb.config
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def config(self, text):
        with open(os.path.join(self.sb.config, "config.ini"), "w") as f:
            f.write(text)

    def test_flat_price(self):
        self.config("[power]\nprice_per_kwh = 0.2\ncurrency = USD\n")
        r = self.m.payback(self.db, 1000, watts=500, hours_per_day=10, rent_per_hour=0.5)
        self.assertAlmostEqual(r["rent_monthly_usd"], round(0.5 * 10 * 30.44, 2))
        self.assertAlmostEqual(r["electricity_monthly_usd"], round(0.5 * 10 * 30.44 * 0.2, 2))
        self.assertAlmostEqual(r["payback_months"], round(1000 / (0.5 * 10 * 30.44 * 0.8), 1))

    def test_from_cloud_history_in_twd(self):
        self.config("[power]\ntariff = tou\ncurrency = TWD\n\n[general]\nusd_to_local = 32\n")
        self.m.record_cloud(self.db, [dict(provider="vast", id="1", name="a", status="running", billing=True,
                                           gpu="4090", gpu_count=2, usd_per_hour=0.8, gpu_util=90)], 1000)
        r = self.m.payback(self.db, 1600, watts=450, hours_per_day=8, t=2000)
        self.assertEqual(r["rent_per_hour"], 0.4)             # 兩張卡 $0.8/h -> 每張 $0.4
        # 每天 8 小時都排得進離峰：夏月 2.27、非夏月 2.15，一年平均
        avg = (2.27 * 4 + 2.15 * 8) / 12
        self.assertAlmostEqual(r["electricity_monthly_usd"], round(0.45 * 8 * 30.44 * avg / 32, 2))

    def test_never_pays_back(self):
        self.config("[power]\nprice_per_kwh = 5\ncurrency = USD\n")
        r = self.m.payback(self.db, 1000, watts=1000, hours_per_day=24, rent_per_hour=0.1)
        self.assertIsNone(r["payback_months"])
        self.assertIn("never pays back", self.m.render_payback(r))
