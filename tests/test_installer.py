import os
import shutil
import subprocess
import sys
import unittest

from tests import helpers


@unittest.skipIf(os.name == "nt", "POSIX installer")
class Installer(unittest.TestCase):
    def test_local_checkout_installs_exact_file_without_fetching(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        prefix = os.path.join(sb.root, "install with spaces")
        env = sb.env(PREFIX=prefix, COMPUTAI_URL="http://127.0.0.1:1/must-not-fetch")
        r = subprocess.run(["sh", "install.sh"], cwd=helpers.ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        installed = os.path.join(prefix, "bin", "computai")
        with open(helpers.SCRIPT, "rb") as f, open(installed, "rb") as g:
            self.assertEqual(f.read(), g.read())
        r = subprocess.run([sys.executable, installed, "--version"], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(helpers.load().__version__, r.stdout)

    def test_download_installer_pins_release_and_accepts_ref_override(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        installer = os.path.join(sb.root, "install.sh")
        shutil.copyfile(os.path.join(helpers.ROOT, "install.sh"), installer)
        bin_dir = os.path.join(sb.root, "tools")
        os.makedirs(bin_dir)
        curl = os.path.join(bin_dir, "curl")
        with open(curl, "w", encoding="utf-8") as f:
            f.write('#!/bin/sh\nprintf "%s\\n" "$2" > "$FETCH_LOG"\ncp "$SOURCE_SCRIPT" "$4"\n')
        os.chmod(curl, 0o755)
        for ref in (None, "custom-ref"):
            log = os.path.join(sb.root, "fetch.log")
            env = sb.env(PREFIX=os.path.join(sb.root, "installed"), FETCH_LOG=log, SOURCE_SCRIPT=helpers.SCRIPT,
                         PATH=bin_dir + os.pathsep + os.environ["PATH"])
            env.pop("COMPUTAI_URL", None)
            env.pop("COMPUTAI_REF", None)
            if ref:
                env["COMPUTAI_REF"] = ref
            r = subprocess.run(["sh", installer], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(log, encoding="utf-8") as f:
                url = f.read().strip()
            self.assertEqual(url, "https://raw.githubusercontent.com/Sean-Hawks/computai/%s/computai" % (ref or "v" + helpers.load().__version__))
