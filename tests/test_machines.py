import json
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
        self.assertIn("@@svcinfo llamacpp 8080", self.m.remote_script([("llamacpp", 8080)]))
        self.assertIn("/usr/lib/wsl/lib", s.split("@@cpu")[0])   # WSL 的 nvidia-smi 不在 ssh 的 PATH 裡

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
        self.assertEqual(d["services"][0]["counters"]["qwen3-0.6b-q8_0"], {"prompt": 5000.0, "generation": 1200.0})
        self.assertEqual(d["services"][0]["models"][0]["name"], "qwen3-0.6b-q8_0")   # 從 /v1/models 拿到的名稱
        self.assertEqual(d["services"][0]["running"], 0.0)

    def test_gpu_model_name(self):
        g = self.m.parse_gpu("0, GPU-x, 38, 2729, 16376, 35, 32.38, NVIDIA GeForce RTX 4070 Ti SUPER")
        self.assertEqual((g["model"], g["util"], g["power"]), ("RTX 4070 Ti SUPER", 38.0, 32.38))
        self.assertIsNone(self.m.parse_gpu("0, GPU-x, 38, 2729, 16376, 35, 32.38")["model"])

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
        self.assertEqual(r["requests"], 0)
        s = self.db.execute("SELECT * FROM samples ORDER BY ts").fetchall()
        self.assertEqual(s[0]["power_w"], 310.5 + 60.2 + 100)
        self.assertEqual(s[1]["power_w"], 320.0 + 100)     # 第二張卡讀不到功耗
        self.assertAlmostEqual(s[1]["cpu_pct"], 50.0)
        det = json.loads(s[0]["detail"])
        self.assertEqual([g["util"] for g in det["gpus"]], [85.0, 0.0])
        self.assertEqual((det["mem_total"], det["load"], det["ncpu"]), (64000, [1.0, 0.8, 0.5], 16))
        self.assertEqual(det["services"][0]["kind"], "vllm")
        self.assertEqual([x["ai_active"] for x in s], [1, 1])  # 有請求在跑、計數器在動
        rep = self.m.machine_report(self.db, 0, 2000)[0]
        joules = (470.7 + 420.0) / 2 * 60
        self.assertAlmostEqual(rep["kwh"], round(joules / 3.6e6, 4))
        self.assertEqual(rep["ai_share"], 1.0)
        self.assertEqual(rep["currency"], "TWD")
        self.assertAlmostEqual(rep["energy_cost_usd"], round(joules / 3.6e6 * 3.0 / 30, 4), 4)
        self.assertAlmostEqual(rep["j_per_token"], round(joules / 6000, 3))
        self.assertAlmostEqual(rep["usd_per_mtok"], round(joules / 3.6e6 * 3.0 / 30 / 6000 * 1e6, 4), 3)
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
        self.assertEqual(rep["loaded"][0]["name"], "qwen3:0.6b")
        self.assertIn("loaded: qwen3:0.6b (ollama:11434, 981 MB)", self.m.render_machines([rep]))

    def test_estimate_power(self):
        e = self.m.estimate_power
        self.assertEqual(e({"base_watts": 50}, 200.0, 90, 10), 250.0)
        self.assertEqual(e({"base_watts": 50, "cpu_watts": 100}, 200.0, 90, 40), 290.0)
        self.assertEqual(e({"idle_watts": 10, "max_watts": 110}, None, 50, 20), 60.0)
        self.assertEqual(e({"idle_watts": 10}, None, 50, 20), 10)
        self.assertIsNone(e({}, None, 50, 20))


class Tariff(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        os.makedirs(self.sb.config)
        with open(os.path.join(self.sb.config, "config.ini"), "w") as f:
            f.write("[power]\ncurrency = TWD\ntariff = tou\n")
        self.old = dict(os.environ)
        os.environ["COMPUTAI_CONFIG_DIR"] = self.sb.config
        self.m = helpers.load()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def test_taipower_two_tier(self):
        ps = self.m.power_settings()
        utc8 = lambda y, mo, d, h: self.m.calendar_ts(y, mo, d, h) - 8 * 3600
        # 2026-07-15 是星期三
        self.assertEqual(self.m.price_at(utc8(2026, 7, 15, 10), ps), (5.54, True))
        self.assertEqual(self.m.price_at(utc8(2026, 7, 15, 8), ps), (2.27, False))
        self.assertEqual(self.m.price_at(utc8(2026, 7, 18, 10), ps), (2.27, False))   # 星期六全天離峰
        self.assertEqual(self.m.price_at(utc8(2026, 11, 11, 12), ps), (2.15, False))  # 非夏月中午離峰
        self.assertEqual(self.m.price_at(utc8(2026, 11, 11, 15), ps), (5.39, True))
        self.assertEqual(self.m.parse_hours("6-11, 14-24, junk, 9-3"), [(6, 11), (14, 24)])

    def test_peak_ai_saving(self):
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        t0 = self.m.calendar_ts(2026, 7, 15, 10) - 8 * 3600       # 夏月平日尖峰
        for k in range(2):
            db.execute("INSERT INTO samples (machine, ts, power_w, ai_active) VALUES ('box', ?, 1000, 1)",
                       (t0 + 600 * k,))
        r = self.m.machine_report(db, t0, t0 + 3600)[0]
        kwh = 1000 * 600 / 3.6e6
        self.assertAlmostEqual(r["energy_cost"], round(kwh * 5.54, 4))
        self.assertAlmostEqual(r["offpeak_saving"], round(kwh * (5.54 - 2.27), 4))
        self.assertIn("moving it off-peak saves", self.m.render_energy([r]))


class SshControl(unittest.TestCase):
    @unittest.skipIf(os.name == "nt", "POSIX only")
    def test_control_dir_is_private(self):
        import shutil
        import tempfile
        short = tempfile.mkdtemp(prefix="ca-", dir="/tmp")   # socket 路徑有長度上限，用短的目錄
        self.addCleanup(shutil.rmtree, short, True)
        old = dict(os.environ)
        try:
            os.environ["COMPUTAI_DATA_DIR"] = short
            m = helpers.load()
            d = m.ssh_control_dir()
            self.assertTrue(d.startswith(short))
            self.assertEqual(os.stat(d).st_mode & 0o777, 0o700)
            os.environ["COMPUTAI_DATA_DIR"] = "/" + "x" * 120
            self.assertIsNone(m.ssh_control_dir())
        finally:
            os.environ.clear()
            os.environ.update(old)


class SshErrors(unittest.TestCase):
    def test_hints(self):
        m = helpers.load()
        self.assertIn("known_hosts", m.ssh_hint("Host key verification failed."))
        self.assertIn("BatchMode", m.ssh_hint("user@h: Permission denied (publickey)."))
        self.assertIn("Tailscale", m.ssh_hint("no answer within 25 s"))
        self.assertEqual(m.ssh_hint("something else"), "")

    def test_run_cmd_collects_stderr(self):
        m = helpers.load()
        errs = []
        out = m.run_cmd(["sh", "-c", "echo 'Host key verification failed.' >&2; exit 255"], errors=errs)
        self.assertEqual(out, "")
        self.assertEqual(errs, ["Host key verification failed."])
        errs = []
        m.run_cmd(["sh", "-c", "sleep 5"], timeout=1, errors=errs)
        self.assertEqual(errs, ["no answer within 1 s"])

    def test_unreachable_machine_becomes_alert(self):
        sb = helpers.Sandbox()
        old = dict(os.environ)
        try:
            os.makedirs(sb.config)
            with open(os.path.join(sb.config, "config.ini"), "w") as f:
                f.write("[machines]\nbox = nowhere\n")
            os.environ.update(COMPUTAI_CONFIG_DIR=sb.config, COMPUTAI_FIXTURES=FX)
            m = helpers.load()
            db = m.open_ledger(":memory:")
            m.ssh_errors["nowhere"] = "Host key verification failed."
            m.sample_machines(db)
            a = m.machine_alerts()
            self.assertEqual(a[0]["machine"], "box")
            self.assertIn("box (nowhere): cannot read: Host key verification failed.; its host key", a[0]["message"])
            db.close()
        finally:
            os.environ.clear()
            os.environ.update(old)
            sb.close()


class Discover(unittest.TestCase):
    def test_ssh_config_hosts(self):
        m = helpers.load()
        self.assertEqual(m.ssh_config_hosts(helpers.fixture("ssh", "config")),
                         ["100.64.0.5", "gpu1", "gpu2", "quoted", "bastion"])

    def test_discover_merges_tailscale_and_reports(self):
        m = helpers.load()
        m.ssh_config_hosts = lambda path=None: ["100.64.0.5", "gpu1"]
        m.tailscale_peers = lambda: [("homelab", "100.64.0.5", "linux", True), ("phone", "100.64.0.9", "android", True),
                                     ("nas", "100.64.0.7", "linux", True), ("old", "100.64.0.8", "linux", False)]
        m.machines = lambda cp=None: [{"host": "gpu1"}]
        m.try_ssh = lambda h, timeout=8: (True, "Linux x86_64") if h != "100.64.0.7" else (False, "Host key verification failed.")
        found = {r["host"]: r for r in m.discover()}
        self.assertEqual(sorted(found), ["100.64.0.5", "100.64.0.7", "gpu1"])   # 手機和離線的不試
        self.assertEqual(found["100.64.0.5"]["name"], "homelab")
        self.assertTrue(found["gpu1"]["configured"])
        text = m.render_discover(list(found.values()))
        self.assertIn("homelab = 100.64.0.5", text)
        self.assertNotIn("gpu1 = gpu1", text)            # 已經設定過的不再建議
        self.assertIn("known_hosts", text)


class Plugs(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(COMPUTAI_CONFIG_DIR=self.sb.config, COMPUTAI_FIXTURES=helpers.fixture("plugs"),
                          HA_URL="http://ha.local:8123", HA_TOKEN="SECRET")
        self.m = helpers.load()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        self.sb.close()

    def test_read_plugs(self):
        r = self.m.read_plug
        self.assertEqual(r("shelly:192.168.1.50"), 187.4)
        self.assertEqual(r("shelly1:10.0.0.2"), 95.5)
        self.assertEqual(r("tasmota:plug.lan"), 64.0)
        self.assertEqual(r("ha:sensor.gpu_box_power"), 420.0)      # kW 換成 W
        self.assertIsNone(r("nope:1.2.3.4"))
        self.assertIsNone(r("shelly:bad host; rm -rf"))            # 不合法的主機名稱直接拒絕
        self.assertEqual(self.m.plug_url("tasmota:1.2.3.4")[1], "http://1.2.3.4/cm?cmnd=Status%208")

    def test_plug_overrides_estimate(self):
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        m = {"name": "box", "plug": "shelly:1.2.3.4", "idle_watts": 10, "max_watts": 20}
        self.m.record_sample(db, m, {"cpu": ("pct", 50.0), "gpus": [], "services": []}, 100)
        self.assertEqual(db.execute("SELECT power_w FROM samples").fetchone()[0], 187.4)
