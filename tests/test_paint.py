import unittest

from tests import helpers


class Paint(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.m.set_style(theme="classic")

    def test_no_color_means_no_escape_codes(self):
        m = self.m
        m.set_style(color=False)
        out = m.gradbar(50, 10) + m.spark([0, 50, 100], 6) + "".join(m.panel("T", "r", ["x"], 20, 80))
        self.assertNotIn("\033", out)
        self.assertEqual(m.gradbar(50, 10), "▕" + "█" * 5 + "░" * 5 + "▏")

    def test_cyber_theme(self):
        m = self.m
        m.set_style(color=False, theme="cyber")
        self.assertEqual(m.heat(0), m.heat(100))                    # 沒有熱度漸層，一律品牌青
        self.assertEqual(m.gradbar(50, 4), "\u2588\u2588\u2591\u2591")          # 沒顏色時用 █ ░，比例看得出來
        m.set_style(color=True, theme="cyber")
        self.assertEqual(m.gradbar(50, 4).count("\u2586"), 4)                 # 有顏色：▆ 粗長條
        m.set_style(color=False, theme="cyber")
        self.assertEqual(m.limit_level(42), "brand")
        self.assertEqual(m.limit_level(85), "warn")
        self.assertEqual(m.limit_level(100), "fail")
        self.assertEqual(m.temp_color(70), m.MAG)
        self.assertEqual(m.temp_color(92), m.RED)
        rows = m.panel("NODE", "x", ["a"], 20, foot="SSH")
        self.assertTrue(rows[0].startswith("\u256d") and " NODE " in rows[0])  # 圓角細框，標題在上框線
        self.assertIn("SSH", rows[-2])                                 # 來源列在最下面
        self.assertTrue(rows[-1].startswith("\u2570"))
        self.assertTrue(all(m.vlen(r) == 20 for r in rows))
        self.assertEqual(m.badge("fail", "ALERT"), "[ALERT]")         # 沒有顏色時用方括號
        m.set_style(theme="classic")

    def test_heat_endpoints(self):
        self.assertEqual(self.m.heat(0), (46, 204, 113))
        self.assertEqual(self.m.heat(100), (231, 76, 60))

    def test_spark_scaling_and_padding(self):
        m = self.m
        m.set_style(color=False)
        self.assertEqual(m.spark([0, 100], 4), "··▁█")
        self.assertEqual(m.spark([150], 1, top=300), "▅")
        self.assertEqual(m.spark([], 3), "···")

    def test_relative_spark_is_single_colour_and_flat_in_the_middle(self):
        m = self.m
        m.set_style(color=False)
        self.assertEqual(m.spark([5, 5, 5], 3, relative=True), "\u2585" * 3)
        self.assertEqual(m.spark([10, 20], 2, relative=True)[-1], "\u2588")
        m.set_style(color=True)
        out = m.spark([1, 2, 3], 3, color=(1, 2, 3), relative=True)
        self.assertEqual(out.count("38;2;1;2;3m"), 3)
        m.set_style()

    def test_panel_width_and_clip_keep_colors_intact(self):
        m = self.m
        m.set_style(color=True)
        rows = m.panel("NODE", "right side", ["a" * 50, m.rgb((1, 2, 3), "專案" * 20)], 30, 50)
        self.assertTrue(all(m.vlen(r) == 30 for r in rows))
        self.assertTrue(rows[2].count("\033[") % 2 == 0)

    def test_ascii_mode(self):
        m = self.m
        m.set_style(color=False, ascii_=True)
        out = "".join(m.panel("T", "", [m.gradbar(30, 4), m.spark([10, 90], 2)], 16))
        self.assertTrue(all(ord(c) < 128 for c in out))
        m.set_style()


if __name__ == "__main__":
    unittest.main()


class HtmlThemes(unittest.TestCase):
    def test_report_and_recap_follow_theme(self):
        m = helpers.load()
        r = {"year": 2026, "tokens": 1, "api_equivalent_usd": 1.0, "value_ratio": None, "active_days": 1,
             "longest_streak": 1, "busiest_day": None, "top_models": []}
        self.assertIn('<body class="cyber">', m.render_recap_html(r, "cyber"))
        self.assertNotIn('class="cyber"', m.render_recap_html(r, "classic"))
        self.assertIn("--s1:#00a3bf", m.REPORT_CSS)                 # 驗證過的霓虹配色


class Wrap(unittest.TestCase):
    def test_wrap(self):
        m = helpers.load()
        self.assertEqual(m.wrap("one two three four", 9), ["one two", "three", "four"])
        lines = m.wrap("對話暫停超過五分鐘後下一則訊息會重新送", 10)
        self.assertTrue(all(m.vlen(x) <= 10 for x in lines))
        self.assertEqual("".join(lines), "對話暫停超過五分鐘後下一則訊息會重新送")
        self.assertEqual(m.wrap("", 5), [""])


class HudPrimitives(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.m.set_style(color=False, theme="cyber")

    def test_bigtext(self):
        rows = self.m.bigtext("10%")
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({len(r) for r in rows}), 1)                  # 三列一樣寬
        self.assertEqual(len(rows[0]), 3 * 4 - 1)                          # 每字 3 欄 + 1 格間距
        self.assertEqual(self.m.bigtext("8"), ["█▀█", "█▀█", "▀▀▀"])

    def test_braille(self):
        self.assertEqual(self.m.braille([0, 100], 1, 100), ["⢸"])     # 左邊空、右邊滿
        self.assertEqual(self.m.braille([100, 100], 1, 100, rows=2), ["⣿", "⣿"])
        self.assertEqual(self.m.braille([], 3, 100), ["⠀" * 3])
