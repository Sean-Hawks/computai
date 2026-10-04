"""Exercise the container test command without requiring a Docker daemon."""
import os
import subprocess
import sys
import unittest

from tests import helpers


@unittest.skipIf(os.name == "nt", "POSIX shell runner")
class DockerRunner(unittest.TestCase):
    def test_unittest_failure_reaches_the_caller(self):
        sb = helpers.Sandbox()
        self.addCleanup(sb.close)
        for name, body in {
            "python3": '#!/bin/sh\necho "synthetic test result"\nexit "$TEST_EXIT"\n',
            "docker": ('#!' + sys.executable + '\nimport os, subprocess, sys\n'
                       'command = sys.argv[-1]\n'
                       'command = command[command.index("test_log="):]\n'
                       'sys.exit(subprocess.call(["sh", "-c", command]))\n'),
        }.items():
            path = os.path.join(sb.root, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            os.chmod(path, 0o755)
        for test_exit in (0, 17):
            with self.subTest(test_exit=test_exit):
                env = dict(os.environ, PATH=sb.root + os.pathsep + os.environ["PATH"], TEST_EXIT=str(test_exit))
                r = subprocess.run(["sh", "tests/docker.sh", "python:3.8-slim"], cwd=helpers.ROOT,
                                   env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0 if test_exit == 0 else 1, r.stderr)
                self.assertIn("synthetic test result", r.stdout)
