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
