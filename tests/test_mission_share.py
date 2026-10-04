import unittest
import xml.etree.ElementTree as ET
from tests import helpers
from tests.test_wrapped import seed, PRICES, SECRET, SESSION


class MissionShare(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.db = self.m.open_ledger(':memory:')
        self.addCleanup(self.db.close)
        seed(self.m, self.db)
        self.data = self.m.history_profile(self.db, self.m.calendar_ts(2026, 10, 4, 12), PRICES)

    def test_every_layout_theme_has_real_counts_and_private_fields_are_absent(self):
        for layout, size in self.m.CREATOR_LAYOUTS.items():
            for theme in ('dark', 'light'):
                svg = self.m.render_mission_share_svg(self.data, 'month-2026-09', '<script>名字</script>', layout, theme, 'zh')
                root = ET.fromstring(svg)
                self.assertEqual((int(root.attrib['width']), int(root.attrib['height'])), size)
                content = ' '.join(root.itertext())
                self.assertIn('12,904,000 tokens', content)
                self.assertNotIn('2026.08', content)
                self.assertNotIn(SECRET, svg)
                self.assertNotIn(SESSION, svg)
                self.assertNotIn('<script>', svg)
                self.assertNotIn('pattern', svg)
                self.assertNotIn('linearGradient', svg)
                self.assertNotIn('opacity=', svg)
                self.assertIn('id="creator-name"', svg)
                for rect in root.findall('.//{http://www.w3.org/2000/svg}rect'):
                    x, y = float(rect.attrib.get('x', 0)), float(rect.attrib.get('y', 0))
                    w, h = float(rect.attrib['width']), float(rect.attrib['height'])
                    self.assertGreaterEqual(w, 0)
                    self.assertGreaterEqual(h, 0)
                    self.assertLessEqual(x + w, size[0] + 1)
                    self.assertLessEqual(y + h, size[1] + 1)

    def test_calm_default_is_independent_of_custom_legacy_colors(self):
        svg = self.m.render_profile_share_svg(self.data, colors=('#123456', '#abcdef'))
        self.assertNotIn('#123456', svg)
        self.assertIn('#f5f5f5', svg)
        with self.assertRaises(ValueError):
            self.m.render_mission_share_svg(self.data, layout='bad')

    def test_monthly_trend_marks_incomplete_month_without_claiming_full_history(self):
        self.m.add_usage(self.db, [dict(source='local', uid='oct', ts=self.m.calendar_ts(2026, 10, 1), output=1000)])
        data = self.m.history_profile(self.db, self.m.calendar_ts(2026, 10, 4, 12), PRICES)
        svg = self.m.render_mission_share_svg(data, 'all', layout='portrait', lang='zh')
        content = ' '.join(ET.fromstring(svg).itertext())
        self.assertIn('2026-10*: 1,000 tokens', content)
        self.assertIn('* 截至目前', content)
        wide = self.m.render_mission_share_svg(data, 'year-2026', layout='wide', lang='zh')
        self.assertIn('輸出 token', ' '.join(ET.fromstring(wide).itertext()))
