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


if __name__ == "__main__":
    unittest.main()
