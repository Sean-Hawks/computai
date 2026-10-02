import os
import unittest

from tests import helpers

FX = helpers.fixture("machines")


class Snapshot(unittest.TestCase):
    def setUp(self):
        os.environ["COMPUTAI_FIXTURES"] = FX
        self.m = helpers.load()
        self.svc = self.m.service_list(self.m.DEFAULT_SERVICES)

    def tearDown(self):
        os.environ.pop("COMPUTAI_FIXTURES", None)

    def test_service_list(self):
        self.assertEqual(self.m.service_list("ollama:11434, nope:1, vllm:x, vllm:8000"),
                         [("ollama", 11434), ("vllm", 8000)])

    def test_script_probes_services(self):
        s = self.m.remote_script([("ollama", 11434), ("vllm", 8000)])
        self.assertIn("echo '@@svc ollama 11434'", s)
        self.assertIn("get http://127.0.0.1:8000/metrics | grep -E '^(vllm:", s)

    def test_mac_with_ollama(self):
        d = self.m.snapshot("mac", self.svc)
        self.assertEqual(d["cpu"][0], "pct")
        self.assertEqual(d["mem_total"], 16384)
        g = d["gpus"][0]
        self.assertEqual((g["vendor"], g["model"]), ("apple", "Apple M3 10-core"))
        self.assertIsNotNone(g["util"])
        self.assertEqual(len(d["services"]), 1)
        svc = d["services"][0]
        self.assertEqual(svc["kind"], "ollama")
        self.assertEqual(svc["models"][0]["name"], "qwen3:0.6b")
        self.assertEqual(svc["models"][0]["vram_mb"], 981)

    def test_nvidia_box_with_vllm(self):
        a = self.m.snapshot("gpubox", self.svc)
        b = self.m.snapshot("gpubox", self.svc)
        self.assertEqual([g["util"] for g in a["gpus"]], [85.0, 0.0])
        self.assertEqual(b["gpus"][1]["util"], None)        # [N/A]
        self.assertEqual(a["gpus"][0]["power"], 310.5)
        self.assertAlmostEqual(self.m.cpu_pct(b["cpu"], a["cpu"]), 50.0)  # 1000 忙 / 2000
        self.assertEqual(len(a["services"]), 1)              # 空的 ollama 回應等於沒開
        v = a["services"][0]
        self.assertEqual(v["running"], 2.0)
        self.assertEqual(v["counters"]["Qwen/Qwen3-32B"], {"prompt": 100000.0, "generation": 20000.0})

    def test_amd_and_llamacpp(self):
        d = self.m.snapshot("amdbox", self.svc)
        self.assertEqual([g["idx"] for g in d["gpus"]], ["0", "1"])   # card0 排在 card1 前面
        self.assertEqual(d["gpus"][1]["power"], 18.0)
        self.assertEqual(d["gpus"][1]["mem_used"], 8192.0)
        self.assertEqual(d["services"][0]["counters"]["llamacpp"], {"prompt": 5000.0, "generation": 1200.0})
        self.assertEqual(d["services"][0]["running"], 0.0)

    def test_unreachable(self):
        self.assertIsNone(self.m.snapshot("nowhere", self.svc))

    def test_control_chars_removed(self):
        self.assertEqual(self.m.untrusted("a\x1b]52;c;x\x07b\n"), "a]52;c;xb\n")


if __name__ == "__main__":
    unittest.main()


class Sampling(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        os.makedirs(self.sb.config)
        with open(os.path.join(self.sb.config, "config.ini"), "w") as f:
            f.write("[machines]\ngpubox = gpubox\nmac = mac\n\n"
                    "[machine.gpubox]\nservices = vllm:8000\nbase_watts = 100\n\n"
                    "[machine.mac]\nservices = ollama:11434\nidle_watts = 6\nmax_watts = 30\n\n"
                    "[power]\nprice_per_kwh = 3.0\ncurrency = TWD\nidle_alert_minutes = 15\n\n"
                    "[general]\nusd_to_local = 30\n")
        self.old = dict(os.environ)
        os.environ.update(COMPUTAI_FIXTURES=FX, COMPUTAI_CONFIG_DIR=self.sb.config)
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def sample_at(self, t, only=None):
        os.environ["COMPUTAI_FAKE_NOW"] = str(t)
        return self.m.sample_machines(self.db, only=only)

    def test_vllm_counters_become_usage_and_energy(self):
        self.sample_at(1000, ["gpubox"])
        self.sample_at(1060, ["gpubox"])
        rows = self.db.execute("SELECT * FROM usage WHERE source = 'local'").fetchall()
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual((r["input"], r["output"], r["model"], r["project"]), (60000, 6000, "Qwen/Qwen3-32B", "gpubox"))
        self.assertEqual(r["cost_usd"], 0.0)
        s = self.db.execute("SELECT * FROM samples ORDER BY ts").fetchall()
        self.assertEqual(s[0]["power_w"], 310.5 + 60.2 + 100)
        self.assertEqual(s[1]["power_w"], 320.0 + 100)     # 第二張卡讀不到功耗
        self.assertAlmostEqual(s[1]["cpu_pct"], 50.0)
        self.assertEqual([x["ai_active"] for x in s], [1, 1])  # 有請求在跑、計數器在動
        rep = self.m.machine_report(self.db, 0, 2000)[0]
        joules = (470.7 + 420.0) / 2 * 60
        self.assertAlmostEqual(rep["kwh"], round(joules / 3.6e6, 4))
        self.assertEqual(rep["ai_share"], 1.0)
        self.assertEqual(rep["currency"], "TWD")
        self.assertAlmostEqual(rep["energy_cost_usd"], round(joules / 3.6e6 * 3.0 / 30, 4), 4)
        self.assertAlmostEqual(rep["j_per_token"], round(joules / 6000, 3))
        self.assertIn("gpubox", self.m.render_machines([rep]))

    def test_counter_reset(self):
        m = {"name": "box"}
        svc = lambda p, g: {"cpu": None, "gpus": [], "services": [
            {"kind": "vllm", "port": 8000, "models": [], "running": 0,
             "counters": {"q": {"prompt": p, "generation": g}}}]}
        self.m.record_sample(self.db, m, svc(1000, 100), 10)
        self.m.record_sample(self.db, m, svc(1500, 150), 20)
        rows = self.m.record_sample(self.db, m, svc(40, 4), 30)   # 服務重開，計數器從頭算
        self.assertEqual((rows[0]["input"], rows[0]["output"]), (40, 4))
        total = self.db.execute("SELECT SUM(input), SUM(output) FROM usage").fetchone()
        self.assertEqual(tuple(total), (540, 54))

    def test_unreachable_machine_is_skipped(self):
        self.sample_at(1000, ["gpubox"])
        self.sample_at(1060, ["gpubox"])
        self.assertIsNone(self.sample_at(1120, ["gpubox"])["gpubox"])   # 沒有第三份輸出
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM samples").fetchone()[0], 2)

    def test_idle_model_alert(self):
        for i in range(5):           # 20 分鐘，每 5 分鐘一次，模型一直載入但 expires_at 沒動
            self.sample_at(10000 + 300 * i, ["mac"])
        alerts = self.m.idle_alerts(self.db, t=10000 + 1200)
        self.assertEqual(len(alerts), 1)
        a = alerts[0]
        self.assertEqual((a["machine"], a["models"], a["idle_minutes"]), ("mac", ["qwen3:0.6b"], 20))
        self.assertIn("idle for 20m", a["message"])
        self.assertEqual(self.m.idle_alerts(self.db, t=10000 + 1200, minutes=30), [])
        # 太久沒有取樣就不知道現在的狀況，不發警示
        self.assertEqual(self.m.idle_alerts(self.db, t=10000 + 1200 + 3600), [])
        # Mac 沒有功耗讀數，用設定的閒置／滿載功耗估
        rep = self.m.machine_report(self.db, 0, 20000)[0]
        self.assertGreater(rep["kwh"], 0)
        self.assertEqual(rep["ai_share"], 0.0)

    def test_estimate_power(self):
        e = self.m.estimate_power
        self.assertEqual(e({"base_watts": 50}, 200.0, 90, 10), 250.0)
        self.assertEqual(e({"idle_watts": 10, "max_watts": 110}, None, 50, 20), 60.0)
        self.assertEqual(e({"idle_watts": 10}, None, 50, 20), 10)
        self.assertIsNone(e({}, None, 50, 20))
