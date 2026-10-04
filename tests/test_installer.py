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
            self.assertEqual(url, "https://raw.githubusercontent.com/Sean-Hawks/computai/%s/computai" % (ref or "v0.1.0-beta.2"))

    def test_install_and_create_runs_without_path_refresh_or_configuration_wizard(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        prefix = os.path.join(sb.root, 'new install')
        env = sb.env(PREFIX=prefix, COMPUTAI_URL='http://127.0.0.1:1/must-not-fetch')
        result = subprocess.run(['sh', 'install.sh', '--create', '--no-open'], cwd=helpers.ROOT,
                                env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Card creator:', result.stdout)
        self.assertNotIn('add ', result.stdout)
        self.assertNotIn('next:', result.stdout)
        self.assertTrue(os.path.isfile(os.path.join(sb.data, 'creator.html')))
        self.assertFalse(os.path.exists(os.path.join(sb.root, '.git')))

    def test_invalid_installer_option_does_not_install(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        for args in (['--no-open'], ['--typo']):
            result = subprocess.run(['sh', 'install.sh'] + args, cwd=helpers.ROOT,
                                    env=sb.env(PREFIX=sb.root), capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
        self.assertFalse(os.path.exists(os.path.join(sb.root, 'bin')))

    def test_install_and_recap_opens_same_monthly_route_without_path_refresh(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        prefix = os.path.join(sb.root, 'monthly install')
        result = subprocess.run(['sh', 'install.sh', '--recap', '--no-open'], cwd=helpers.ROOT,
                                env=sb.env(PREFIX=prefix, COMPUTAI_URL='http://127.0.0.1:1/must-not-fetch'),
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Recap page:', result.stdout)
        self.assertIn('No observed usage', result.stdout)
        self.assertNotIn('next:', result.stdout)
        self.assertTrue(os.path.isfile(os.path.join(sb.data, 'creator.html')))

    def test_released_beta_installer_explains_missing_creator_before_installing(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        installer = os.path.join(sb.root, 'install.sh')
        shutil.copyfile(os.path.join(helpers.ROOT, 'install.sh'), installer)
        prefix = os.path.join(sb.root, 'never installed')
        env = sb.env(PREFIX=prefix)
        env.pop('COMPUTAI_REF', None)
        env.pop('COMPUTAI_URL', None)
        for ref in ('v0.1.0-beta.1', 'v0.1.0-beta.2'):
            for entry in ('--recap', '--create'):
                result = subprocess.run(['sh', installer, entry], env=dict(env, COMPUTAI_REF=ref),
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 2)
                self.assertIn('beta.1 and beta.2 do not include', result.stderr)
                self.assertFalse(os.path.exists(prefix))
                self.assertFalse(os.path.exists(sb.data))

    def test_mac_launcher_uses_its_own_folder_and_skips_installation(self):
        from unittest import mock
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        # Fake interpreter records the launch; it never opens a real browser.
        tools = os.path.join(sb.root, 'tools')
        folder = os.path.join(sb.root, 'portable folder')
        os.makedirs(tools)
        os.makedirs(folder)
        launcher = os.path.join(folder, 'Make a card.command')
        shutil.copyfile(os.path.join(helpers.ROOT, 'Make a card.command'), launcher)
        fake = os.path.join(tools, 'python3')
        with open(fake, 'w') as f:
            f.write('#!/bin/sh\nif [ "$1" = "-c" ]; then exit 0; fi\npwd > "$LAUNCH_LOG"\nprintf "%s\\n" "$@" >> "$LAUNCH_LOG"\n')
        os.chmod(fake, 0o755)
        log = os.path.join(sb.root, 'launch.log')
        result = subprocess.run(['sh', launcher], cwd=sb.root,
                                env=sb.env(PATH=tools + os.pathsep + os.environ['PATH'], LAUNCH_LOG=log),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(log) as f:
            self.assertEqual(f.read().splitlines(), [folder, './computai', 'recap', '--lang', 'zh'])
