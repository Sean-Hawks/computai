import json
import os
import stat
import tempfile
import unittest

from tests import helpers

FAKE = r"""#!/usr/bin/env python3
import json, os, sys
for line in sys.stdin:
    m = json.loads(line)
    if m.get("id") == 1:
        print(json.dumps({"id": 1, "result": {"userAgent": "fake"}}), flush=True)
    elif m.get("id") == 2:
        print(json.dumps({"id": 2, "result": {
            "accountId": "acct-SECRET", "ordinaryUsageAllowed": True,
            "rateLimitResetCredits": {"availableCount": 1, "credits": None},
            "rateLimits": {"planType": "pro", "primary": {
                "usedPercent": 80 if os.environ.get("CODEX_HOME", "").endswith("-nycu") else 39, "windowDurationMins": 10080,
                                                          "resetsAt": 1791593542},
                           "secondary": {"usedPercent": 12, "windowDurationMins": 300, "resetsAt": 1791000000}}}}),
              flush=True)
        break
"""


class CodexAccount(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        path = os.path.join(self.tmp, "codex")
        with open(path, "w") as f:
            f.write(FAKE)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        self.old = dict(os.environ)
        os.environ["PATH"] = self.tmp + os.pathsep + os.environ["PATH"]
        os.environ.pop("COMPUTAI_FIXTURES", None)
        self.m = helpers.load()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old)
        import shutil
        shutil.rmtree(self.tmp)

    @unittest.skipIf(os.name == "nt", "fake codex is a POSIX script")
    def test_reads_account_limits_through_the_codex_cli(self):
        rows, credits = self.m.codex_account_limits(t=1790000000)
        self.assertEqual(credits, 1)
        self.assertEqual([(r["name"], r["used_percent"], r["window_minutes"], r["resets_at"]) for r in rows],
                         [("week", 39.0, 10080, 1791593542), ("5h", 12.0, 300, 1791000000)])
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        self.assertEqual(self.m.codex_account_poll(db, t=1790000000), 2)
        self.assertEqual(self.m.codex_account_poll(db, t=1790000600), 0)        # 沒變就不寫
        dump = "\n".join(db.iterdump())
        self.assertNotIn("acct-SECRET", dump)                                    # 帳號 ID 不留
        self.assertEqual(db.execute("SELECT value FROM meta WHERE key = 'codex_reset_credits'").fetchone()[0], "1")

    @unittest.skipIf(os.name == "nt", "fake codex is a POSIX script")
    def test_polls_every_listed_account(self):
        os.environ["CODEX_HOME"] = ",".join(os.path.join(self.tmp, d) for d in (".codex", ".codex-nycu"))
        db = self.m.open_ledger(":memory:")
        self.addCleanup(db.close)
        self.m.codex_account_poll(db, t=1790000000)
        got = {(r["account"], r["used_percent"]) for r in self.m.current_limits(db, t=1790000000) if r["name"] == "week"}
        self.assertEqual(got, {("", 39.0), ("nycu", 80.0)})
        keys = {r[0] for r in db.execute("SELECT key FROM meta WHERE key LIKE 'codex_reset_credits%'")}
        self.assertEqual(keys, {"codex_reset_credits", "codex_reset_credits:nycu"})

    def test_no_codex_cli(self):
        os.environ["PATH"] = "/nonexistent"
        self.assertEqual(self.m.codex_account_limits(), ([], None))


if __name__ == "__main__":
    unittest.main()
