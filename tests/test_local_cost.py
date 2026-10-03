import os
import unittest

from tests import helpers

T0 = 1790000000
PRICES = {"claude-haiku-4": {"input": 1.0, "output": 5.0, "cache_read": 0.1, "cache_write_5m": 1.25, "cache_write_1h": 2.0},
          "claude-opus-5-5": {"input": 5.0, "output": 25.0, "cache_read": 0.5, "cache_write_5m": 6.25, "cache_write_1h": 10.0},
          "gpt-5.4": {"input": 2.5, "output": 15.0, "cache_read": 0.25, "cache_write_5m": 2.5, "cache_write_1h": 0}}


class LocalCost(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(self.sb.env(COMPUTAI_FAKE_NOW=str(T0)))
        os.makedirs(self.sb.config)
        with open(os.path.join(self.sb.config, "config.ini"), "w") as f:
            f.write("[local]\ncompare_models = claude-haiku-4, gpt-5.4-mini\nhardware_usd = 1200\nlifetime_years = 2\n"
                    "[energy]\ngrid_kg_per_kwh = 0.5\n")
        self.m = helpers.load()
        self.m.set_lang("en")
        self.db = self.m.open_ledger()
        # gpubox 這個月：2 度電都在跑 AI，電費 $0.40，輸出 4M token
        self.m.machine_report = lambda db, s, e, ps=None: [
            {"machine": "gpubox", "kwh": 2.0, "ai_kwh": 2.0, "energy_cost_usd": 0.4, "output_tokens": 4000000,
             "j_per_token": 1.8}]
        self.m.add_usage(self.db, [
            {"source": "local", "uid": "l1", "ts": T0 - 3600, "project": "gpubox", "model": "qwen3:8b",
             "input": 1000000, "output": 4000000},
            # 輕量請求：輸出少、上下文小；重的那筆不算
            {"source": "claude", "uid": "c1", "ts": T0 - 600, "model": "claude-opus-5-5", "input": 2000, "output": 300},
            {"source": "claude", "uid": "c2", "ts": T0 - 500, "model": "claude-opus-5-5", "input": 2000, "cache_read": 200000,
             "output": 5000},
        ])
        # 另一台只有跑分紀錄
        self.db.execute("INSERT INTO bench_runs VALUES (?, 'mac', 'ollama:11434', 'qwen3:1.7b', 40, 20, 0.5, 0.05)", (T0 - 86400,))
        self.db.commit()

    def tearDown(self):
        self.db.close()
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def report(self):
        start, end, _ = self.m.month_range()
        return self.m.local_cost_report(self.db, start, end, prices=PRICES)

    def test_per_model_cost_breakeven_and_bench(self):
        r = self.report()
        q = [x for x in r["models"] if x["model"] == "qwen3:8b"][0]
        self.assertEqual(q["elec_usd_per_mtok"], 0.08)                         # $0.40 ÷ 5M token
        self.assertEqual(q["depreciation_usd_per_mtok"], 10.0)                  # $1200 ÷ 24 個月 ÷ 5M token
        haiku = q["vs"][0]
        self.assertEqual((haiku["model"], haiku["api_usd_per_mtok"]), ("claude-haiku-4", 3.0))
        self.assertAlmostEqual(haiku["breakeven_mtok_per_month"], round(50 / (3.0 - 0.08), 2))   # $50/月 ÷ 每 M 省多少
        b = [x for x in r["models"] if x["model"] == "qwen3:1.7b"][0]
        self.assertEqual((b["source"], b["elec_usd_per_mtok"]), ("bench", 0.05))
        self.assertEqual(r["compare"], ["claude-haiku-4"])
        self.assertEqual(r["missing_prices"], ["gpt-5.4-mini"])                # 不會被字首當成 gpt-5.4

    def test_light_requests_month_and_carbon(self):
        r = self.report()
        lt = r["light"]
        self.assertEqual(lt["requests"], 1)                                     # 只有輕的那筆
        self.assertAlmostEqual(lt["api_usd"], round((2000 * 5 + 300 * 25) / 1e6, 2))
        self.assertEqual(r["best"], {"machine": "mac", "model": "qwen3:1.7b"})  # 每 M 最便宜的本地模型
        mo = r["month"]
        self.assertEqual((mo["kwh"], mo["co2_kg"]), (2.0, 1.0))
        self.assertAlmostEqual(mo["saved_usd"], round(5.0 * 3.0 - 0.4, 2))      # 5M token 照 haiku 價格，扣掉電費
        text = self.m.render_local_cost(r, "2026-09")
        self.assertIn("This month local models saved you $14.60", text)
        self.assertIn("no exact price for gpt-5.4-mini", text)


if __name__ == "__main__":
    unittest.main()
