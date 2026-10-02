import os
import unittest

from tests import helpers

FX = helpers.fixture("api")
PRICES = None


class AdminApi(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(COMPUTAI_FIXTURES=FX, COMPUTAI_CONFIG_DIR=self.sb.config,
                          COMPUTAI_FAKE_NOW="1790500000")
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def test_anthropic_usage_report_with_pages(self):
        self.assertEqual(self.m.sync_anthropic_api(self.db), 2)
        rows = {r["model"]: r for r in self.db.execute("SELECT * FROM usage WHERE source = 'anthropic-api'")}
        s = rows["claude-sonnet-5-5"]
        self.assertEqual((s["input"], s["cache_write_5m"], s["cache_read"], s["output"]),
                         (120000, 40000, 900000, 30000))
        self.assertEqual(rows["claude-haiku-4-5"]["cache_write_1h"], 2000)
        self.assertEqual(self.m.sync_anthropic_api(self.db), 0)       # 再抓一次不會重複

    def test_openai_usage(self):
        self.assertEqual(self.m.sync_openai_api(self.db), 1)
        r = self.db.execute("SELECT * FROM usage WHERE source = 'openai-api'").fetchone()
        self.assertEqual((r["input"], r["cache_read"], r["output"], r["requests"], r["model"]),
                         (30000, 20000, 8000, 42, "gpt-5.5"))

    def test_window_starts_at_last_sync(self):
        self.assertEqual(self.m.api_days(self.db, "x"), (1790500000 - 31 * 86400) // 86400 * 86400)
        self.m.mark_api(self.db, "x")
        self.assertEqual(self.m.api_days(self.db, "x"), (1790500000 - 86400) // 86400 * 86400)

    def test_no_key_no_call(self):
        os.environ.pop("COMPUTAI_FIXTURES")
        for k in ("ANTHROPIC_ADMIN_KEY", "OPENAI_ADMIN_KEY"):
            os.environ.pop(k, None)
        def boom(*a, **k):
            raise AssertionError("should not call the API without a key")
        self.m.api_json = boom
        self.assertEqual(self.m.sync_anthropic_api(self.db), 0)
        self.assertEqual(self.m.sync_openai_api(self.db), 0)


if __name__ == "__main__":
    unittest.main()
