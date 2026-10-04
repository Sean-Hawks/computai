import copy
import json
import os
import unittest

from tests import helpers


class SpendDashboard(unittest.TestCase):
    def setUp(self):
        self.sandbox = helpers.Sandbox()
        self.old_env = dict(os.environ)
        os.environ.update(self.sandbox.env())
        self.module = helpers.load()
        self.module.set_lang("en")
        with open(helpers.fixture("spend", "dashboard.json"), encoding="utf-8") as fixture:
            self.state = json.load(fixture)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)
        self.sandbox.close()

    def test_separates_known_projected_and_equivalent(self):
        before = copy.deepcopy(self.state)
        result = self.module.spend_summary(self.state)
        self.assertAlmostEqual(result["known_usd"], 315.79)
        self.assertAlmostEqual(result["remaining_usd"], 109.84)
        self.assertAlmostEqual(result["value_usd"], 274.67)
        self.assertAlmostEqual(sum(row["usd"] for row in result["payments"]), result["known_usd"])
        self.assertAlmostEqual(result["providers"][0]["ratio"], 2.2849)
        self.assertEqual(self.state, before)

    def test_configured_plan_without_usage_remains_in_bill(self):
        self.state["sources"] = []
        result = self.module.spend_summary(self.state)
        self.assertEqual(len(result["providers"]), 2)
        self.assertEqual(result["value_usd"], 0)
        self.assertEqual(result["providers"][1]["fee_usd"], 200)

    def test_missing_and_zero_fee_do_not_invent_ratios(self):
        del self.state["forecast"]["subscription_by_source"]["claude"]
        self.state["forecast"]["subscription_by_source"]["codex"]["usd"] = 0
        result = self.module.spend_summary(self.state)
        self.assertEqual(result["missing_plans"], ["claude"])
        self.assertTrue(all(row["ratio"] is None for row in result["providers"]))

    def test_older_snapshot_can_use_source_plans(self):
        plans = self.state["forecast"].pop("subscription_by_source")
        for row in self.state["sources"]:
            if row["source"] in plans:
                row["plan"] = plans[row["source"]]
        self.assertAlmostEqual(self.module.spend_summary(self.state)["providers"][0]["ratio"], 2.2849)

    def test_older_snapshot_with_unpriced_models_cannot_claim_complete_ratios(self):
        self.state["unpriced_models"] = ["example-unpriced"]
        result = self.module.spend_summary(self.state)
        self.assertFalse(result["value_complete"])
        self.assertTrue(all(row["ratio"] is None for row in result["providers"]))

    def test_forecast_includes_configured_plans_without_usage(self):
        os.makedirs(self.sandbox.config)
        with open(os.path.join(self.sandbox.config, "config.ini"), "w") as config:
            config.write("[plans]\nclaude = Example, 100, 2026-10-04\n")
        database = self.module.open_ledger()
        try:
            result = self.module.forecast(database, t=1791100800, month_machines=[])
        finally:
            database.close()
        self.assertEqual(result["subscription_by_source"]["claude"]["usd"], 100)
        self.assertEqual(result["subscriptions_usd"], 100)

    def ledger_state(self, rows, plans="claude = Example, 100, test\ncodex = Example, 10, test\n"):
        os.makedirs(self.sandbox.config)
        with open(os.path.join(self.sandbox.config, "config.ini"), "w") as config:
            config.write("[plans]\n" + plans)
        os.environ["COMPUTAI_FAKE_NOW"] = "1791100800"
        self.module.load_prices = lambda: {"example-priced": dict(input=1, output=2, cache_read=0,
                                                                 cache_write_5m=0, cache_write_1h=0)}
        database = self.module.open_ledger(":memory:")
        try:
            self.module.add_usage(database, [dict(row, uid=str(i), ts=1791100000)
                                             for i, row in enumerate(rows)])
            self.state = self.module.dashboard_state(database)
        finally:
            database.close()
        return self.module.spend_summary(self.state)

    def test_unpriced_subscription_is_not_zero_value_or_a_zero_ratio(self):
        result = self.ledger_state([dict(source="claude", model="example-unpriced", output=1000)])
        self.assertEqual(self.state["sources"][0]["unpriced_models"], ["example-unpriced"])
        self.assertFalse(result["value_complete"])
        self.assertIsNone(result["providers"][0]["ratio"])
        self.assertTrue(result["providers"][1]["value_complete"])  # unused configured plan
        for lang in ("zh", "en"):
            for width in (60, 90, 160):
                for height in (20, 36, 60):
                    with self.subTest(lang=lang, width=width, height=height):
                        text = self.render(width=width, height=height, lang=lang)
                        self.assertIn("$0.00+", text)
                        self.assertIn("僅已定價部分" if lang == "zh" else "Priced portion only", text)
                        self.assertLessEqual(len(text.splitlines()), height - 7)
                        self.assertTrue(all(self.module.vlen(line) <= width for line in text.splitlines()))
                        for ascii_ in (False, True):
                            screen = self.module.render_live(self.state, width, height=height, theme_name="cyber",
                                                             view="spend", ascii_=ascii_)
                            self.assertIn("$0.00+", screen)
                            self.assertLessEqual(len(screen.splitlines()), height)

    def test_partial_prices_suppress_only_the_affected_source_ratio(self):
        result = self.ledger_state([
            dict(source="claude", model="example-unpriced", output=1000),
            dict(source="claude", model="example-priced", output=1000000),
            dict(source="codex", model="example-priced", output=1000000)])
        self.assertEqual(result["value_usd"], 4)
        claude, codex = result["providers"]
        self.assertEqual(claude["value_usd"], 2)
        self.assertIsNone(claude["ratio"])
        self.assertFalse(claude["value_complete"])
        self.assertTrue(codex["value_complete"])
        self.assertEqual(codex["ratio"], 0.2)
        self.assertIn("$4.00+", self.render())
        self.assertIn("0.20x", self.render())

    def test_unpriced_api_does_not_hide_a_complete_subscription_comparison(self):
        result = self.ledger_state([
            dict(source="openai", model="example-unpriced", output=1000),
            dict(source="claude", model="example-priced", output=1000000)])
        self.assertTrue(result["value_complete"])
        self.assertEqual(result["providers"][0]["ratio"], 0.02)
        self.assertIn("Unpriced models", self.render())
        self.assertNotIn("$2.00+", self.render())

    def test_missing_and_zero_fees_survive_real_snapshot_aggregation(self):
        result = self.ledger_state([
            dict(source="claude", model="example-priced", output=1000000),
            dict(source="codex", model="example-priced", output=1000000)],
            plans="codex = Free, 0, test\n")
        self.assertEqual(result["known_usd"], 0)
        self.assertEqual(result["value_usd"], 4)
        self.assertEqual(result["missing_plans"], ["claude"])
        self.assertTrue(all(row["ratio"] is None for row in result["providers"]))
        text = self.render()
        self.assertIn("Not set", text)
        self.assertNotIn("0.00x", text)

    def render(self, width=160, height=60, lang="en", color=False, ascii_=False):
        self.module.set_lang(lang)
        self.module.set_style(color, ascii_, "cyber")
        return "\n".join(self.module.spend_panels(self.state, width, height))

    def test_layout_keeps_cash_and_value_separate(self):
        result = self.render()
        for label in ("KNOWN MONTHLY COST", "MONTH-END FORECAST", "SUBSCRIPTION API VALUE",
                      "COST BREAKDOWN", "SUBSCRIPTION COMPARISON", "$315.79", "$425.63", "$274.67",
                      "$109.84", "$74.37", "$100.00", "$200.00", "2.28x", "0.23x", "Electricity", "not cash savings"):
            self.assertIn(label, result)
        self.assertNotIn("actually pay", result)
        self.assertIn("month 800M tokens", result)
        self.assertIn("Last 5 days", result)
        self.assertIn("2026-09-30", result)

    def test_widths_languages_and_terminal_modes(self):
        for lang in ("zh", "en"):
            for width in (60, 78, 90, 107, 108, 139, 140, 160, 220):
                for color, ascii_ in ((False, False), (True, False), (False, True)):
                    with self.subTest(lang=lang, width=width, color=color, ascii_=ascii_):
                        result = self.render(width=width, lang=lang, color=color, ascii_=ascii_)
                        self.assertTrue(all(self.module.vlen(line) <= width for line in result.splitlines()))
                        for amount in ("$315.79", "$425.63", "$274.67", "$228.49", "$46.18"):
                            self.assertIn(amount, result)
                        if ascii_:
                            if lang == "en":
                                self.assertTrue(result.isascii())

    def test_short_terminal_preserves_primary_amounts(self):
        for lang in ("zh", "en"):
            for width in (60, 90, 160):
                result = self.render(width=width, height=20, lang=lang)
                self.assertLessEqual(len(result.splitlines()), 13)
                for amount in ("$315.79", "$425.63", "$274.67"):
                    self.assertIn(amount, result)

    def test_medium_terminal_falls_back_instead_of_losing_bottom_rows(self):
        for lang in ("zh", "en"):
            for width in (60, 90, 160):
                for height in (30, 36, 40, 50, 60):
                    result = self.render(width=width, height=height, lang=lang)
                    self.assertLessEqual(len(result.splitlines()), height - 7)
                    for amount in ("$315.79", "$425.63", "$274.67"):
                        self.assertIn(amount, result)

    def test_missing_prices_plans_and_zero_fees_are_visible(self):
        del self.state["forecast"]["subscription_by_source"]["claude"]
        self.state["forecast"]["subscription_by_source"]["codex"]["usd"] = 0
        self.state["unpriced_models"] = ["example-unpriced"]
        result = self.render()
        self.assertIn("Missing fees", result)
        self.assertIn("Unpriced models", result)
        self.assertNotIn("0.00x", result)
        self.assertNotIn("2.28x", result)

    def test_zero_usage_and_configured_unused_plans(self):
        self.state["sources"] = []
        self.state["daily"] = {"days": [], "sources": {}}
        result = self.render()
        self.assertIn("Example Max", result)
        self.assertIn("Example Pro", result)
        self.assertIn("$0.00", result)
        self.assertIn("No daily usage records yet", result)

    def test_no_budget_and_over_budget(self):
        self.state["forecast"]["budget_usd"] = None
        self.assertIn("No budget set", self.render())
        self.state["forecast"]["budget_usd"] = 300
        result = self.render(color=True)
        self.assertIn("projected over $125.63", result)
        self.assertIn("38;2;248;113;113", result)

    def test_money_above_a_thousand_retains_cents_and_long_plan(self):
        self.state["forecast"]["projected_usd"] = 12345.67
        self.state["forecast"]["subscription_by_source"]["claude"]["name"] = "Example plan " * 8
        for width in (60, 160):
            result = self.render(width=width)
            self.assertIn("$12,345.67", result)
            self.assertTrue(all(self.module.vlen(line) <= width for line in result.splitlines()))

    def test_advice_is_wrapped_and_limited_with_escape_hatch(self):
        self.state["insights"] = [{"text": "Example advice " * 30} for index in range(5)]
        result = self.render(height=60)
        self.assertIn("computai --insights", result)
        self.assertTrue(all(self.module.vlen(line) <= 160 for line in result.splitlines()))

    def test_short_terminal_still_warns_about_incomplete_costs(self):
        self.state["forecast"]["subscription_by_source"] = {}
        self.state["unpriced_models"] = ["example-unpriced"]
        for lang in ("zh", "en"):
            result = self.render(width=60, height=20, lang=lang)
            self.assertLessEqual(len(result.splitlines()), 13)
            self.assertIn("低估" if lang == "zh" else "understate", result)

    def test_layout_snapshots(self):
        for lang in ("zh", "en"):
            for size, width, height in (("wide", 160, 60), ("narrow", 60, 60), ("compact", 60, 20)):
                name = "spend-%s-%s.txt" % (size, lang)
                path = os.path.join(helpers.ROOT, "tests", "golden", name)
                result = self.render(width=width, height=height, lang=lang)
                if os.environ.get("COMPUTAI_UPDATE_GOLDEN"):
                    with open(path, "w", encoding="utf-8") as golden:
                        golden.write(result)
                with open(path, encoding="utf-8") as golden:
                    self.assertEqual(result, golden.read(), name)


if __name__ == "__main__":
    unittest.main()
