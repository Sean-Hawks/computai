import contextlib
import io
import json
import os
import time
import unittest
from unittest import mock

from tests import helpers


class LocalHistory(unittest.TestCase):
    def setUp(self):
        self.sb = helpers.Sandbox()
        self.old = dict(os.environ)
        os.environ.update(self.sb.env(COMPUTAI_FAKE_NOW="1791075600", TZ="UTC"))
        if hasattr(time, "tzset"):
            time.tzset()
        self.m = helpers.load()
        self.m.set_lang("en")
        self.m.set_style(False, False)
        self.db = self.m.open_ledger()
        self.t = int(self.m.now())
        self.m.add_usage(self.db, [
            {"source": "local", "uid": "proxy-a", "ts": self.t - 30, "session": "proxy", "model": "qwen3:8b",
             "project": "box", "input": 10, "cache_read": 5, "output": 40},
            {"source": "local", "uid": "counter-a", "ts": self.t - 20, "session": "vllm", "model": "qwen3:8b",
             "project": "box", "input": 30, "output": 70, "requests": 0},
            {"source": "local", "uid": "proxy-b", "ts": self.t - 10, "session": "proxy", "model": "tiny",
             "project": "laptop", "input": 4, "output": 8},
            {"source": "claude", "uid": "not-local", "ts": self.t - 1, "output": 999},
            {"source": "local", "uid": "yesterday", "ts": self.t - 86400, "output": 123},
        ])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        os.environ.clear()
        os.environ.update(self.old)
        if hasattr(time, "tzset"):
            time.tzset()
        self.sb.close()

    def test_latest_rows_filters_and_usage_allowlist(self):
        history = self.m.local_history(self.db)
        rows = history["rows"]
        self.assertEqual([r["kind"] for r in rows], ["proxy", "counter", "proxy"])
        self.assertEqual(rows[1]["requests"], None)
        self.assertEqual((rows[2]["input"], rows[2]["requests"]), (15, 1))
        self.assertEqual(set(rows[0]), {"ts", "machine", "model", "input", "output", "kind", "requests"})
        self.assertEqual(history["end"] - history["start"], 86400)
        self.assertEqual(len(self.m.local_history(self.db, limit=1)["rows"]), 1)
        self.assertEqual(len(self.m.local_history(self.db, machine="box", model="QWEN3:8B")["rows"]), 2)
        self.assertEqual(self.m.local_history(self.db, machine="' OR 1=1 --")["rows"], [])
        self.assertEqual(len(self.m.local_history(self.db, start=self.t - 86401, end=self.t - 86400 + 1)["rows"]), 1)

    def test_invalid_limit_and_cli_does_not_sync(self):
        for limit in (0, -1, 201):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                self.m.parse_args(["--local-history", str(limit)])
        out = io.StringIO()
        with mock.patch.object(self.m, "sync", side_effect=AssertionError("must not sync")), contextlib.redirect_stdout(out):
            self.assertEqual(self.m.run(self.m.parse_args(["--local-history", "2", "--json"]), self.db), 0)
        self.assertEqual(len(json.loads(out.getvalue())["rows"]), 2)
        self.assertEqual(self.m.parse_args(["--local-history"]).local_history, 20)

    def test_display_width_and_untrusted_names(self):
        history = self.m.local_history(self.db)
        history["rows"][0]["model"] = "long-model-" * 8 + "\x1b[2J\x07"
        for lang in ("en", "zh"):
            self.m.set_lang(lang)
            for color in (False, True):
                self.m.set_style(color, False)
                for width in (40, 60, 80, 100, 145):
                    for height in (None, 12, 20):
                        with self.subTest(lang=lang, color=color, width=width, height=height):
                            lines = self.m.render_local_history(history, width, height)
                            self.assertTrue(all(self.m.vlen(ln) <= width for ln in lines), lines)
                            if height:
                                self.assertLessEqual(len(lines), height)
                            text = "\n".join(lines)
                            self.assertNotIn("\x1b[2J", text)
                            self.assertNotIn("\x07", text)

    def test_dashboard_and_local_tab_include_history(self):
        state = self.m.dashboard_state(self.db)
        self.assertEqual(len(state["local_history"]["rows"]), 3)
        for width in (60, 100, 145):
            for height in (30, 40, 47):
                with self.subTest(width=width, height=height):
                    text = self.m.render_live(state, width, height=height, theme_name="cyber", view="local")
                    self.assertTrue(all(self.m.vlen(ln) <= width for ln in text.splitlines()))
                    self.assertLessEqual(len(text.splitlines()), height)
                    self.assertTrue("Recent local inference" in text or "computai --local-history" in text)
        self.assertIn("function localHistoryCard", self.m.WEB_JS)
        self.assertNotIn("innerHTML", self.m.WEB_JS)
        self.m.set_style(False, True)
        history_text = "\n".join(self.m.render_local_history(state["local_history"], 60))
        self.assertTrue(all(ord(c) < 128 for c in history_text))

    def test_empty_history_explains_capture(self):
        history = self.m.local_history(self.db, machine="absent")
        self.assertIn("--proxy", "\n".join(self.m.render_local_history(history, 60)))


if __name__ == "__main__":
    unittest.main()
