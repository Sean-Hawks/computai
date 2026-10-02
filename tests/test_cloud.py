import json
import os
import unittest

from tests import helpers

FX = helpers.fixture("cloud")


class Cloud(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(COMPUTAI_FIXTURES=FX, COMPUTAI_CONFIG_DIR=self.sb.config)
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def fetch(self):
        insts, errors = self.m.fetch_clouds()
        self.assertEqual(errors, [])
        return {i["id"]: i for i in insts}

    def test_normalized(self):
        i = self.fetch()
        self.assertEqual(len(i), 7)
        busy, idle, off = i["pod-busy"], i["pod-idle"], i["pod-off"]
        self.assertEqual((busy["billing"], busy["usd_per_hour"], busy["gpu"], busy["gpu_util"]),
                         (True, 2.69, "H100 SXM", 97.0))
        self.assertEqual((idle["gpu_count"], idle["gpu_util"]), (2, 0.5))     # 兩張卡平均
        self.assertEqual((off["billing"], off["usd_per_hour"]), (False, 0))
        v = i["1234567"]
        self.assertEqual((v["billing"], v["usd_per_hour"], v["gpu_util"], v["name"]), (True, 1.6021, 2.0, "sweep-a"))
        self.assertEqual(i["7654321"]["usd_per_hour"], 0.02)                  # 停機只收儲存費
        lam = i["0920582c7ff041399e34823a0be62549"]
        self.assertEqual((lam["usd_per_hour"], lam["gpu_util"], lam["gpu"]), (2.49, None, "H100 (80 GB PCIe)"))
        self.assertFalse(i["aaaa"]["billing"])

    def test_spend_and_idle_alert(self):
        insts = list(self.fetch().values())
        for k in range(4):                       # 每 10 分鐘看一次，看 30 分鐘
            self.m.record_cloud(self.db, insts, 100000 + 600 * k)
        rows = self.db.execute("SELECT project, SUM(cost_usd) FROM usage WHERE source = 'cloud' "
                               "GROUP BY project ORDER BY project").fetchall()
        spent = {r[0]: round(r[1], 4) for r in rows}
        self.assertEqual(spent["runpod/train-llm"], round(2.69 * 0.5, 4))
        self.assertEqual(spent["vast/sweep-a"], round(1.6021 * 0.5, 4))
        self.assertNotIn("runpod/old-volume", spent)
        alerts = self.m.cloud_alerts(self.db, t=100000 + 1800)
        kinds = sorted((a["kind"], a["id"]) for a in alerts)
        self.assertEqual(kinds, [("cloud_idle_billing", "1234567"), ("cloud_idle_billing", "pod-idle"),
                                 ("cloud_unknown_util", "0920582c7ff041399e34823a0be62549")])
        idle = [a for a in alerts if a["id"] == "pod-idle"][0]
        self.assertEqual(idle["idle_minutes"], 30)
        self.assertEqual(idle["wasted_usd"], 0.22)
        self.assertIn("still billing $0.44/h", idle["message"])
        # 門檻 20 分鐘：才看了 10 分鐘的時候還不警示
        self.assertEqual([a for a in self.m.cloud_alerts(self.db, t=100000 + 600)
                          if a["kind"] == "cloud_idle_billing" and a["id"] == "pod-idle"], [])

    def test_gap_too_long_not_charged(self):
        insts = list(self.fetch().values())
        self.m.record_cloud(self.db, insts, 0)
        self.m.record_cloud(self.db, insts, 7 * 3600)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM usage").fetchone()[0], 0)

    def test_cli_and_summary(self):
        env = dict(COMPUTAI_FIXTURES=FX, COMPUTAI_FAKE_NOW=1790000000)
        r = self.sb.run("--cloud", **env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("runpod/forgot-me", r.stdout)
        self.sb.run("--cloud", "--json", COMPUTAI_FIXTURES=FX, COMPUTAI_FAKE_NOW=1790001800)
        d = json.loads(self.sb.run("--summary", "--json", "--no-sync", "--month", "2026-09",
                                   COMPUTAI_FAKE_NOW=1790001800).stdout)
        cloud = [x for x in d["sources"] if x["source"] == "cloud"][0]
        self.assertAlmostEqual(cloud["cost_usd"], (2.69 + 0.44 + 1.6021 + 0.02 + 2.49) / 2, 3)
        self.assertTrue(any(a["kind"] == "cloud_idle_billing" for a in d["alerts"]))

    def test_errors_do_not_leak_keys(self):
        os.environ.pop("COMPUTAI_FIXTURES")
        os.environ["RUNPOD_API_KEY"] = "rp_SECRET123"
        def boom(*a, **k):
            raise self.m.ApiError("runpod: HTTP 401 from the pods API")
        self.m.api_json = boom
        insts, errors = self.m.fetch_clouds(only=["runpod"])
        self.assertEqual(insts, [])
        self.assertNotIn("SECRET", " ".join(errors))


if __name__ == "__main__":
    unittest.main()
