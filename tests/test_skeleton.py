import os
import unittest

from tests import helpers


class Paths(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()

    def tearDown(self):
        self.sb.close()

    def test_env_overrides(self):
        r = self.sb.run("--paths")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(self.sb.config, r.stdout)
        self.assertIn(self.sb.data, r.stdout)

    def test_xdg_defaults(self):
        m = helpers.load()
        old = dict(os.environ)
        try:
            for k in ("COMPUTAI_CONFIG_DIR", "COMPUTAI_DATA_DIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME"):
                os.environ.pop(k, None)
            os.environ["XDG_DATA_HOME"] = "/x/data"
            self.assertEqual(m.data_dir(), os.path.join("/x/data", "computai"))
            if os.name != "nt":
                self.assertTrue(m.config_dir().endswith(os.path.join(".config", "computai")))
        finally:
            os.environ.clear()
            os.environ.update(old)

    def test_version(self):
        r = self.sb.run("--version")
        self.assertIn("computai", r.stdout)


if __name__ == "__main__":
    unittest.main()
