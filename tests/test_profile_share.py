import json
import os
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

from tests import helpers
from tests.test_wrapped import PRICES, SECRET, SESSION, seed


class ProfileShare(unittest.TestCase):
    def setUp(self):
        if hasattr(time, 'tzset'):
            os.environ['TZ'] = 'UTC'
            time.tzset()
        self.m = helpers.load()
        self.db = self.m.open_ledger(':memory:')
        self.addCleanup(self.db.close)
        seed(self.m, self.db)
        self.data = self.m.history_profile(self.db, self.m.calendar_ts(2026, 10, 4, 12), PRICES)

    def render(self, **kwargs):
        return self.m.render_profile_share_svg(self.data, **kwargs)

    def test_dimensions_static_svg_privacy_and_style(self):
        for layout, size in self.m.SHARE_LAYOUTS.items():
            for lang in ('en', 'zh'):
                with self.subTest(layout=layout, lang=lang):
                    svg = self.render(layout=layout, lang=lang, style='amber', handle='hawks')
                    root = ET.fromstring(svg)
                    self.assertEqual((int(root.attrib['width']), int(root.attrib['height'])), size)
                    self.assertIn('#a78bfa', svg)
                    self.assertIn('#fbbf24', svg)
                    self.assertIn('SYS.HAWKS', svg)
                    self.assertNotIn(SECRET, svg)
                    self.assertNotIn(SESSION, svg)
                    self.assertNotIn('<script', svg)
                    self.assertNotIn('animation', svg)
                    self.assertNotIn('href=', svg)
                    self.assertNotIn('http://', svg.replace('http://www.w3.org/2000/svg', ''))
                    for rect in root.findall('.//{http://www.w3.org/2000/svg}rect'):
                        self.assertGreaterEqual(float(rect.attrib.get('width', 0)), 0)
                        self.assertGreaterEqual(float(rect.attrib.get('height', 0)), 0)

    def test_selected_month_has_exact_buckets_and_no_other_periods(self):
        svg = self.render(selected='month-2026-09', layout='portrait', lang='zh')
        root = ET.fromstring(svg)
        content = ' '.join(root.itertext())
        self.assertIn('2026-09 月回顧', content)
        self.assertIn('12,904,000 tokens', content)
        self.assertIn('快取讀取: 8,000,000', content)
        self.assertIn('產生的輸出 token', content)
        self.assertIn('每日處理量', content)
        self.assertNotIn('2026.08', content)
        self.assertNotIn('API', content.replace('AI_OPS', ''))
        self.assertNotIn('方案回本', content)

    def test_partial_year_and_unknown_period(self):
        text = ' '.join(ET.fromstring(self.render(selected='year-2026', lang='zh')).itertext())
        self.assertIn('截至目前', text)
        self.assertIn('2026.08.20 - 2026.10.04', text)
        with self.assertRaises(ValueError):
            self.render(selected='year-2025')
        with self.assertRaises(ValueError):
            self.render(layout='unknown')

    def test_metadata_injection_long_labels_and_custom_colors(self):
        attack = '</text><script>alert(1)</script>' + '長模型名' * 40
        self.m.add_usage(self.db, [dict(source='local', uid='html', ts=self.data['generated_at'] - 10,
                                     model=attack, output=9000000000)])
        self.data = self.m.history_profile(self.db, self.data['generated_at'], PRICES)
        svg = self.render(handle=attack, colors=('#123456', '#abcdef'), layout='wide')
        root = ET.fromstring(svg)
        self.assertNotIn('<script>', svg)
        self.assertIn('#123456', svg)
        self.assertIn('#abcdef', svg)
        text = root.findall('.//{http://www.w3.org/2000/svg}text')
        self.assertTrue(any('…' in (el.text or '') for el in text))
        self.assertTrue(all(len(el.text or '') < 150 for el in text))

    def test_empty_profile_does_not_invent_activity_or_cache(self):
        db = self.m.open_ledger(':memory:')
        try:
            data = self.m.history_profile(db, self.data['generated_at'], {})
            for layout in self.m.SHARE_LAYOUTS:
                svg = self.m.render_profile_share_svg(data, layout=layout, lang='zh')
                content = ' '.join(ET.fromstring(svg).itertext())
                self.assertIn('尚無可見用量', content)
                self.assertNotIn('100.0%', content)
                self.assertNotIn('nan', svg.lower())
        finally:
            db.close()
