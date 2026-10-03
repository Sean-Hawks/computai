import os
import unittest

from tests import helpers

TEXT = """# my settings
[plans]
# what I pay
claude = Pro, 20, x

[power]
price_per_kwh = 3.2   ; summer
"""


class EditIni(unittest.TestCase):
    def setUp(self):
        self.m = helpers.load()

    def test_replace_keeps_comments(self):
        out = self.m.edit_ini(TEXT, "plans", "claude", "Max 5x, 100, 2026-10-03")
        self.assertIn("# what I pay\nclaude = Max 5x, 100, 2026-10-03\n", out)
        self.assertIn("# my settings", out)
        self.assertIn("price_per_kwh = 3.2   ; summer", out)

    def test_add_key_after_last_value(self):
        out = self.m.edit_ini(TEXT, "plans", "codex", "Plus, 20, x")
        self.assertIn("claude = Pro, 20, x\ncodex = Plus, 20, x\n\n[power]", out)

    def test_add_section(self):
        out = self.m.edit_ini(TEXT, "machine.wsl", "base_watts", "60")
        self.assertTrue(out.endswith("\n\n[machine.wsl]\nbase_watts = 60\n"))
        self.assertEqual(self.m.edit_ini("", "a", "b", "c"), "[a]\nb = c\n")

    def test_delete(self):
        out = self.m.edit_ini(TEXT, "plans", "claude", None)
        self.assertNotIn("claude", out)
        self.assertIn("# what I pay", out)
        self.assertEqual(self.m.edit_ini(TEXT, "nope", "x", None), TEXT)

    def test_key_with_regex_chars_and_similar_names(self):
        text = "[machines]\nm1m = 1.2.3.4\nm1m-2 = 5.6.7.8\n"
        out = self.m.edit_ini(text, "machines", "m1m", "9.9.9.9")
        self.assertEqual(out, "[machines]\nm1m = 9.9.9.9\nm1m-2 = 5.6.7.8\n")

    def test_parse_assignment(self):
        self.assertEqual(self.m.parse_assignment("machine.wsl.mac=aa:bb"), ("machine.wsl", "mac", "aa:bb"))
        with self.assertRaises(SystemExit):
            self.m.parse_assignment("nodot=1")


class SetCli(unittest.TestCase):
    def test_set_and_unset(self):
        sb = helpers.Sandbox()
        try:
            r = sb.run("--set", "plans.claude=Max 5x, 100, 2026-10-03", "--set", "power.currency=TWD")
            self.assertEqual(r.returncode, 0, r.stderr)
            path = os.path.join(sb.config, "config.ini")
            text = open(path, encoding="utf-8").read()
            self.assertIn("claude = Max 5x, 100, 2026-10-03", text)
            self.assertIn("currency = TWD", text)
            self.assertIn("# ComputAI settings", text)              # 範本的註解還在
            self.assertTrue(os.path.exists(path + ".bak"))
            sb.run("--unset", "plans.claude")
            self.assertNotIn("claude = Max 5x", open(path, encoding="utf-8").read())
        finally:
            sb.close()


if __name__ == "__main__":
    unittest.main()
