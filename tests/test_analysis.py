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
