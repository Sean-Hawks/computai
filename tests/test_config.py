import contextlib
import io
import os
import unittest

from tests import helpers


class Config(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        os.environ["COMPUTAI_CONFIG_DIR"] = self.sb.config
        self.m = helpers.load()

    def tearDown(self):
        os.environ.pop("COMPUTAI_CONFIG_DIR", None)
        os.environ.pop("COMPUTAI_TEST_KEY", None)
        self.sb.close()

    def write(self, name, text, mode=0o600):
        os.makedirs(self.sb.config, exist_ok=True)
        path = os.path.join(self.sb.config, name)
        with open(path, "w") as f:
            f.write(text)
        os.chmod(path, mode)
        return path

    def test_ensure_config_keeps_user_edits(self):
        self.write("config.ini", "[plans]\nclaude = Pro, 20, 2026-01-01\n")
        self.m.ensure_config()
        self.assertTrue(os.path.exists(os.path.join(self.sb.config, "prices.ini")))
        p = self.m.plans()
        self.assertEqual(p["claude"]["usd"], 20.0)
        self.assertEqual(p["codex"]["usd"], 200.0)  # 沒寫的那個來自預設值

    def test_price_prefix_and_suffix(self):
        path = self.write("prices.ini", "[claude-opus-5-5]\ninput = 4\noutput = 20\ncache_read = 0.2\n"
                                         "[claude-opus-5]\ninput = 5\noutput = 25\n")
        prices = self.m.load_prices(path)
        self.assertEqual(self.m.price_for("claude-opus-5-5[1m]", prices)["input"], 4)
        self.assertEqual(self.m.price_for("claude-opus-5-5-20270101", prices)["input"], 4)
        self.assertEqual(self.m.price_for("claude-opus-5", prices)["input"], 5)
        self.assertIsNone(self.m.price_for("gpt-9", prices))
        # 沒寫快取價格就用輸入價格
        self.assertEqual(prices["claude-opus-5"]["cache_write_1h"], 5)

    @unittest.skipIf(os.name == "nt", "POSIX permissions")
    def test_secret_requires_600(self):
        self.write("secrets.ini", "[secrets]\nCOMPUTAI_TEST_KEY = abc\n", mode=0o644)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertIsNone(self.m.secret("COMPUTAI_TEST_KEY"))
        self.assertIn("chmod 600", err.getvalue())
        self.assertNotIn("abc", err.getvalue())
        os.chmod(os.path.join(self.sb.config, "secrets.ini"), 0o600)
        self.assertEqual(self.m.secret("COMPUTAI_TEST_KEY"), "abc")
        os.environ["COMPUTAI_TEST_KEY"] = "env"
        self.assertEqual(self.m.secret("COMPUTAI_TEST_KEY"), "env")


if __name__ == "__main__":
    unittest.main()


class DefaultPrices(unittest.TestCase):
    def test_default_table_parses_and_covers_seen_models(self):
        m = helpers.load()
        sb = helpers.Sandbox()
        try:
            os.makedirs(sb.config)
            path = os.path.join(sb.config, "prices.ini")
            with open(path, "w") as f:
                f.write(m.DEFAULT_PRICES)
            prices = m.load_prices(path)
        finally:
            sb.close()
        for model, inp in (("claude-opus-4-8", 5), ("claude-opus-5", 5), ("claude-opus-5-5[1m]", 4),
                           ("claude-fable-5", 10), ("claude-fable-5-1", 10), ("claude-sonnet-5-5", 2),
                           ("claude-haiku-4-5-20251001", 1), ("gpt-5.5", 5), ("gpt-6-astra", 10),
                           ("claude-opus-5-5@fast", 8)):
            self.assertEqual(m.price_for(model, prices)["input"], inp, model)
        self.assertEqual(m.price_for("claude-fable-5-1", prices)["cache_read"], 0.25)
        self.assertEqual(m.price_for("claude-fable-5", prices)["cache_read"], 1)
        self.assertEqual(m.price_for("gpt-5.5", prices)["cache_write_5m"], 5)  # 退回輸入價


class InlineComments(unittest.TestCase):
    def test_inline_comments(self):
        sb = helpers.Sandbox()
        try:
            os.makedirs(sb.config)
            with open(os.path.join(sb.config, "config.ini"), "w") as f:
                f.write("[power]\nprice_per_kwh = 3.2   ; summer\ncurrency = TWD # local\n")
            os.environ["COMPUTAI_CONFIG_DIR"] = sb.config
            m = helpers.load()
            ps = m.power_settings()
            self.assertEqual((ps["price_per_kwh"], ps["currency"]), (3.2, "TWD"))
        finally:
            os.environ.pop("COMPUTAI_CONFIG_DIR", None)
            sb.close()
