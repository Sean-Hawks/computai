import os
import time
import unittest
import xml.etree.ElementTree as ET

from tests import helpers
from tests.test_wrapped import PRICES, SECRET, SESSION, seed


class Card(unittest.TestCase):
    def setUp(self):
        if hasattr(time, "tzset"):
            os.environ["TZ"] = "UTC"
            time.tzset()
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)
        self.addCleanup(self.m.set_lang, "en")
        self.m.set_lang("en")
        seed(self.m, self.db)
        self.t = self.m.calendar_ts(2026, 9, 12, 12)

    def card(self, period="30d"):
        return self.m.card_data(self.db, period, PRICES, {}, t=self.t)

    def test_periods(self):
        sept = 4 * 3100000 + 500000 + 4000
        self.assertEqual(self.card("30d")["tokens"], sept + 1000000)      # 8/20 的那筆還在 30 天內
        self.assertEqual(self.card("month")["tokens"], sept)
        self.assertEqual(self.card("year")["tokens"], sept + 1000000)
        self.assertEqual(self.card("all")["tokens"], sept + 1000000)
        with self.assertRaises(SystemExit):
            self.card("week")

    def test_fields_and_bars(self):
        c = self.card("month")
        self.assertEqual((c["top_model"], c["active_days"], c["longest_streak"]), ("claude-opus-5-5", 5, 4))
        self.assertEqual(len(c["bars"]), 14)                              # 最近 14 天，最後一根是今天
        self.assertEqual(c["bars"][-1], 0.0)
        self.assertGreater(c["bars"][13 - 2], 0)                          # 9/10
        self.assertGreater(c["bars"][13 - 11], 0)                         # 9/1
        y = self.card("year")
        self.assertEqual(len(y["bars"]), 12)
        self.assertGreater(y["bars"][-1], 0)                              # 九月
        self.assertGreater(y["bars"][-2], 0)                              # 八月

    def test_svg_dark_and_light(self):
        c = self.card()
        dark, light = self.m.render_card_svg(c, "dark"), self.m.render_card_svg(c, "light")
        for svg in (dark, light):
            root = ET.fromstring(svg)
            self.assertEqual((root.get("width"), root.get("height")), ("495", "195"))
            for bad in ("<script", "<image", "href", "@font-face", "@import", "<style", "onload"):
                self.assertNotIn(bad, svg)
            self.assertEqual(svg.count("http"), 1)                        # 只有 xmlns
            for want in ("last 30 days", "13.9M", "claude-opus-5-5"):
                self.assertIn(want, svg)
            self.assertNotIn("secret", svg)
            self.assertNotIn(SESSION, svg)
        self.assertIn("#0d1117", dark)
        self.assertIn("#ffffff", light)
        self.assertNotEqual(dark, light)

    def test_escapes_model_and_zh(self):
        self.m.add_usage(self.db, [dict(source="claude", uid="evil", ts=self.m.calendar_ts(2026, 9, 11, 3),
                                        model='<b>"&', output=10 ** 11)])
        svg = self.m.render_card_svg(self.card())
        ET.fromstring(svg)
        self.assertNotIn("<b>", svg)
        self.m.set_lang("zh")
        svg = self.m.render_card_svg(self.card("year"), "light")
        ET.fromstring(svg)
        self.assertIn("今年", svg)

    def test_empty_ledger(self):
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        svg = self.m.render_card_svg(self.m.card_data(db, "30d", PRICES, {}, t=self.t))
        ET.fromstring(svg)
        self.assertIn("no usage yet", svg)

    def test_cli_writes_card_and_validates_period(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        out = os.path.join(sb.root, "card.svg")
        r = sb.run("--card", "--svg", out, "--card-theme", "light", "--no-sync")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(out, encoding="utf-8") as f:
            self.assertIn("#ffffff", f.read())
        self.assertNotEqual(sb.run("--card", "--period", "week", "--no-sync").returncode, 0)
        r = sb.run("--card", "--no-sync")                                 # 不指定檔案就印到標準輸出
        self.assertTrue(r.stdout.startswith("<svg"))
