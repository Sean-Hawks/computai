import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import unittest

from tests import helpers

PRICES = {"claude-opus-5-5": {"input": 5.0, "output": 25.0, "cache_read": 0.5,
                              "cache_write_5m": 6.0, "cache_write_1h": 10.0},
          "claude-sonnet-5-5": {"input": 3.0, "output": 15.0, "cache_read": 0.3,
                                "cache_write_5m": 3.75, "cache_write_1h": 6.0}}
PLANS = {"claude": {"name": "Max", "usd": 100.0, "checked": ""}}
SECRET = "/Users/someone/secret-project"
SESSION = "sess-3f9a1c-do-not-leak"


def seed(m, db):
    """2026-09 的合成用量：連續 3 天 + 1 天，大多在凌晨 2 點；8 月較少。"""
    at = lambda mo, d, h: m.calendar_ts(2026, mo, d, h)    # TZ=UTC，所以等於本地時間
    rows = []
    for i, d in enumerate((1, 2, 3, 10)):
        rows.append(dict(source="claude", uid="a%d" % i, ts=at(9, d, 2), model="claude-opus-5-5",
                         project=SECRET, session=SESSION, input=100000, cache_read=2000000,
                         output=1000000, requests=5))
    rows.append(dict(source="claude", uid="b", ts=at(9, 10, 15), model="claude-sonnet-5-5",
                     project=SECRET, session="other", output=500000, requests=1))
    rows.append(dict(source="local", uid="l", ts=at(9, 4, 20), model="qwen3", input=1000, output=3000))
    rows.append(dict(source="claude", uid="p", ts=at(8, 20, 12), model="claude-opus-5-5",
                     output=1000000, requests=2))
    m.add_usage(db, rows)


class Wrapped(unittest.TestCase):
    def setUp(self):
        if hasattr(time, "tzset"):
            os.environ["TZ"] = "UTC"
            time.tzset()
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)
        seed(self.m, self.db)
        self.start, self.end, self.label, self.kind = self.m.wrapped_period("2026-09")
        self.t = self.m.calendar_ts(2026, 10, 3, 12)    # 九月已結束

    def run_wrapped(self, **kw):
        return self.m.wrapped(self.db, self.start, self.end, self.label, self.kind, PRICES, PLANS, t=self.t, **kw)

    def test_period_parsing(self):
        self.assertEqual(self.m.wrapped_period("2026")[2:], ("2026", "year"))
        self.assertEqual(self.m.wrapped_period("2026-9")[3], "month")
        self.assertEqual(self.m.wrapped_period("2026-09")[1] - self.m.wrapped_period("2026-09")[0], 30 * 86400)
        with self.assertRaises(SystemExit):
            self.m.wrapped_period("last week")

    def test_totals_streak_and_days(self):
        w = self.run_wrapped()
        self.assertEqual(w["active_days"], 5)          # 1、2、3、4（本地）、10
        self.assertEqual(w["longest_streak"], 4)
        self.assertEqual(w["busiest_day"], "2026-09-10")
        self.assertEqual(w["tokens"], 4 * 3100000 + 500000 + 4000)
        self.assertEqual(w["output_tokens"], 4000000 + 500000 + 3000)
        self.assertEqual(w["local_tokens"], 4000)
        self.assertEqual(w["subscription_fees_usd"], 100.0)

    def test_streak_function(self):
        f = self.m.longest_streak
        self.assertEqual(f([]), 0)
        self.assertEqual(f(["2026-02-28", "2026-03-01", "2026-03-02", "2026-03-04"]), 3)   # 跨月
        self.assertEqual(f(["2026-12-31", "2027-01-01"]), 2)                               # 跨年
        self.assertEqual(f(["2026-05-01", "2026-05-03"]), 1)

    def test_persona_buckets(self):
        p = self.m.persona_for
        self.assertEqual([p(h) for h in (0, 4, 5, 8, 9, 17, 18, 23)],
                         ["night_owl", "night_owl", "early_bird", "early_bird",
                          "nine_to_five", "nine_to_five", "evening_hacker", "evening_hacker"])
        w = self.run_wrapped()
        self.assertEqual((w["peak_hour"], w["persona"]), (2, "night_owl"))

    def test_weekday_and_models(self):
        w = self.run_wrapped()
        self.assertEqual(w["busiest_weekday"], 3)      # 2026-09-10 是星期四
        self.assertEqual([x["model"] for x in w["top_models"]], ["claude-opus-5-5", "claude-sonnet-5-5", "qwen3"])
        self.assertEqual(sum(x["share_pct"] for x in w["top_models"]), 100)

    def test_sessions_and_cache_savings(self):
        w = self.run_wrapped()
        self.assertEqual(w["sessions"], 2)
        self.assertEqual(w["biggest_session"]["tokens"], 4 * 3100000)
        self.assertEqual(w["biggest_session"]["duration_s"], 9 * 86400)
        self.assertAlmostEqual(w["cache_savings_usd"], 4 * 2000000 * (5.0 - 0.5) / 1e6)

    def test_equivalents(self):
        e = self.m.equivalents(1000000)
        self.assertEqual(e["words"], 750000)
        self.assertEqual(e["lotr"], round(750000 / 480000.0, 2))
        self.assertEqual(e["reading_hours"], 50.0)     # 75 萬字 / 250 字每分
        self.assertEqual(self.m.equivalents(0)["words"], 0)

    def test_previous_period_comparison(self):
        w = self.run_wrapped()
        self.assertEqual(w["previous"]["tokens"], 1000000)
        self.assertEqual(w["previous"]["tokens_change_pct"], round(100.0 * (w["tokens"] - 1000000) / 1000000))
        self.assertGreater(w["previous"]["value_change_pct"], 0)
        # 沒有上一期的資料就沒有百分比
        self.start, self.end, self.label, self.kind = self.m.wrapped_period("2026-08")
        self.assertIsNone(self.run_wrapped()["previous"]["tokens_change_pct"])

    def test_in_progress_month_compares_equal_length(self):
        t = self.m.calendar_ts(2026, 9, 5, 12)
        start, end, label, kind = self.m.wrapped_period("2026-09")
        ps, pe = self.m._previous_period(start, end, kind, t)
        self.assertEqual(ps, self.m.calendar_ts(2026, 8, 1))
        self.assertEqual(pe - ps, t + 1 - start)

    def test_year_compares_previous_year(self):
        s, e, label, kind = self.m.wrapped_period("2026")
        w = self.m.wrapped(self.db, s, e, label, kind, PRICES, PLANS, t=self.t)
        self.assertEqual(w["kind"], "year")
        self.assertEqual(w["previous"]["tokens"], 0)
        self.assertIsNone(w["previous"]["tokens_change_pct"])

    def test_empty_period(self):
        w = self.m.wrapped(self.db, 0, 100, "x", "month", PRICES, PLANS, t=self.t)
        self.assertEqual((w["tokens"], w["active_days"], w["peak_hour"], w["persona"]), (0, 0, None, None))
        self.assertEqual(w["top_models"], [])

    def test_no_private_names_in_data(self):
        blob = json.dumps(self.run_wrapped())
        self.assertNotIn("secret", blob)
        self.assertNotIn("sess-3f9a1c", blob)


class WrappedText(unittest.TestCase):
    def setUp(self):
        if hasattr(time, "tzset"):
            os.environ["TZ"] = "UTC"
            time.tzset()
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)
        seed(self.m, self.db)
        self.addCleanup(self.m.set_lang, "en")
        s, e, label, kind = self.m.wrapped_period("2026-09")
        self.w = self.m.wrapped(self.db, s, e, label, kind, PRICES, PLANS, t=self.m.calendar_ts(2026, 10, 3, 12))

    def test_render_en(self):
        self.m.set_lang("en")
        text = self.m.render_wrapped(self.w)
        for want in ("ComputAI Wrapped 2026-09", "Night owl", "Longest streak: 4 days", "2026-09-10", "Thursday",
                     "The Lord of the Rings", "claude-opus-5-5", "VS LAST MONTH"):
            self.assertIn(want, text)

    def test_render_zh(self):
        self.m.set_lang("zh")
        text = self.m.render_wrapped(self.w)
        for want in ("夜貓子", "最長連續 4 天", "星期四", "《魔戒》"):
            self.assertIn(want, text)

    def test_every_slide_string_exists_in_both_languages(self):
        keys = {k for k in self.m.UI["en"] if k.startswith("wr_")}
        self.assertEqual(keys, {k for k in self.m.UI["zh"] if k.startswith("wr_")})

    def test_render_has_no_private_names(self):
        for lang in ("en", "zh"):
            self.m.set_lang(lang)
            text = self.m.render_wrapped(self.w) + json.dumps(self.m.wrapped_slides(self.w))
            self.assertNotIn("secret", text)
            self.assertNotIn("sess-3f9a1c", text)

    def test_empty_period_slides(self):
        w = self.m.wrapped(self.db, 0, 100, "x", "month", PRICES, PLANS)
        self.assertEqual([s["id"] for s in self.m.wrapped_slides(w)], ["intro", "none"])
        self.assertIn("No usage", self.m.render_wrapped(w))


class WrappedCli(unittest.TestCase):
    def test_json_and_text(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        r = sb.run("--wrapped", "2026-09", "--no-sync", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        w = json.loads(r.stdout)
        self.assertEqual((w["label"], w["kind"], w["tokens"]), ("2026-09", "month", 0))
        r = sb.run("--wrapped", "2026", "--no-sync")
        self.assertIn("ComputAI Wrapped 2026", r.stdout)
        self.assertNotEqual(sb.run("--wrapped", "nonsense", "--no-sync").returncode, 0)
