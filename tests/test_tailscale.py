import os
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

from tests import helpers

# 假的 tailscale：把收到的參數記進 log，status 回一台已登入的機器
FAKE = r"""#!/bin/sh
echo "$*" >> "$TS_LOG"
case "$1" in
  status) echo '{"BackendState": "Running", "Self": {"DNSName": "box.tail1234.ts.net."}}' ;;
  serve) [ "$2" = status ] && echo "${TS_SERVE:-{\}}"; exit 0 ;;
esac
"""


@unittest.skipIf(os.name == "nt", "fake tailscale is a POSIX script")
class Tailscale(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.bin = os.path.join(self.sb.root, "bin")
        os.makedirs(self.bin)
        path = os.path.join(self.bin, "tailscale")
        with open(path, "w") as f:
            f.write(FAKE)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        self.log = os.path.join(self.sb.root, "ts.log")

    def tearDown(self):
        self.sb.close()

    def env(self, with_ts=True, **extra):
        return dict(PATH="/usr/bin:/bin", TS_LOG=self.log,
                    COMPUTAI_TAILSCALE=os.path.join(self.bin, "tailscale") if with_ts else "none", **extra)

    def calls(self):
        try:
            with open(self.log) as f:
                return f.read().splitlines()
        except OSError:
            return []

    def test_opens_serve_and_turns_it_off_on_ctrl_c(self):
        p = subprocess.Popen([sys.executable, helpers.SCRIPT, "--web", "127.0.0.1:0", "--tailscale", "-n", "60"],
                             env=self.sb.env(**self.env()), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out = ""
        try:
            deadline = time.time() + 20
            while time.time() < deadline and "ts.net" not in out:
                out += p.stdout.readline()
            self.assertIn("https://box.tail1234.ts.net/", out)
            port = int(out.split("http://127.0.0.1:")[1].split("/")[0])
            self.assertIn("serve --bg --https=443 %d" % port, self.calls())
            # tailscale serve 轉過來的請求帶 ts.net 的 Host：要放行；別的名字照樣擋
            req = urllib.request.Request("http://127.0.0.1:%d/" % port, headers={"Host": "box.tail1234.ts.net"})
            with urllib.request.urlopen(req, timeout=10) as r:
                self.assertEqual(r.status, 200)
            req = urllib.request.Request("http://127.0.0.1:%d/" % port, headers={"Host": "evil.example"})
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(req, timeout=10)
            cm.exception.close()
        finally:
            p.send_signal(signal.SIGINT)
            p.communicate(timeout=20)
        self.assertEqual(self.calls()[-1], "serve --https=443 off")

    def test_sigterm_also_turns_it_off_and_443_in_use_is_left_alone(self):
        # 這台的 443 已經被別的服務用了：改用 8443，不蓋掉別人的
        p = subprocess.Popen([sys.executable, helpers.SCRIPT, "--web", "127.0.0.1:0", "--tailscale", "-n", "60"],
                             env=self.sb.env(**self.env(TS_SERVE='{"TCP": {"443": {"HTTPS": true}}}')),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out = ""
        deadline = time.time() + 20
        while time.time() < deadline and "ts.net" not in out:
            out += p.stdout.readline()
        self.assertIn("https://box.tail1234.ts.net:8443/", out)
        p.terminate()
        p.communicate(timeout=20)
        self.assertTrue(any(c.startswith("serve --bg --https=8443 ") for c in self.calls()), self.calls())
        self.assertEqual(self.calls()[-1], "serve --https=8443 off")

    def test_without_tailscale_explains_and_never_opens_up(self):
        r = self.sb.run("--web", "127.0.0.1:0", "--tailscale", **self.env(with_ts=False))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("tailscale.com/download", r.stderr)
        self.assertNotIn("dashboard on", r.stdout)
        r = self.sb.run("--web", "0.0.0.0:0", "--tailscale", **self.env())
        self.assertIn("keeps the dashboard on 127.0.0.1", r.stderr)
        self.assertEqual(self.calls(), [])                            # 連 tailscale 都沒叫

    def test_bare_tailscale_means_web(self):
        m = helpers.load()
        args = m.parse_args(["--tailscale"])
        m.serve_web = lambda listen, interval, sample_every, tailscale=False: (listen, tailscale)
        db = m.open_ledger(":memory:")
        self.addCleanup(db.close)
        self.assertEqual(m.run(args, db), ("127.0.0.1:8765", True))


if __name__ == "__main__":
    unittest.main()
