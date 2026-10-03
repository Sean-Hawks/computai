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
        self.assertEqual(m.heat(0), (0, 240, 255))
        self.assertEqual(m.heat(100), (255, 42, 109))
        self.assertEqual(m.gradbar(50, 4), "\u25b0\u25b0\u25b1\u25b1")
        rows = m.panel("NODE", "x", ["a"], 20)
        self.assertTrue(rows[0].startswith("\u250f\u2501\u2501\u252b NODE \u2523"))
        self.assertTrue(all(m.vlen(r) == 20 for r in rows))
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
