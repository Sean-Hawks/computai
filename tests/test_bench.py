import json
import unittest

from tests import helpers


class Bench(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()
        self.m.set_lang("en")

    def test_parse_ollama_and_openai(self):
        ol = json.dumps({"response": "secret text", "eval_count": 200, "eval_duration": 2_000_000_000}) + "\n@@time 2.5\n"
        self.assertEqual(self.m.bench_parse("ollama", ol), (200, 2.0))      # 用 Ollama 自己量的生成時間
        oa = json.dumps({"choices": [{"message": {"content": "x"}}], "usage": {"completion_tokens": 256}}) + "\n@@time 1.6\n"
        self.assertEqual(self.m.bench_parse("vllm", oa), (256, 1.6))
        self.assertIsNone(self.m.bench_parse("vllm", "curl: (7) refused"))

    def test_pick_model(self):
        tags = json.dumps({"models": [{"name": "big", "size": 9e9}, {"name": "small", "size": 1e9}]})
        self.assertEqual(self.m.bench_pick_model("ollama", tags, []), "small")
        self.assertEqual(self.m.bench_pick_model("ollama", tags, ["loaded"]), "loaded")
        self.assertEqual(self.m.bench_pick_model("vllm", json.dumps({"data": [{"id": "Qwen/Qwen3"}]}), []), "Qwen/Qwen3")

    def test_script_cannot_be_broken_by_model_name(self):
        s = self.m.bench_script("ollama", 11434, "x\nCOMPUTAI_EOF\nrm -rf ~")
        self.assertEqual(s.count("\nCOMPUTAI_EOF\n"), 1)                  # 名稱裡的換行被 JSON 跳脫掉了

    def test_render(self):
        b = {"rows": [{"machine": "wsl", "service": "vllm:8000", "model": "qwen3", "tok_s": 150.0, "power_w": 120.0,
                       "j_per_token": 0.8, "usd_per_mtok": 0.0333, "error": None},
                      {"machine": "mac", "service": "ollama:11434", "model": None, "tok_s": None, "power_w": None,
                       "j_per_token": None, "usd_per_mtok": None, "error": "no model to run"}],
             "api_cheapest": {"model": "cheap-api", "usd_per_mtok": 5.0}, "tokens": 256}
        text = self.m.render_bench(b)
        self.assertIn("150.0 tok/s", text)
        self.assertIn("electricity is 150x cheaper", text)
        self.assertIn("no model to run", text)


if __name__ == "__main__":
    unittest.main()
