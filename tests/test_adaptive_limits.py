import os
import shutil
import tempfile
import unittest

from tests import helpers

T0 = 1790000000


class AdaptiveLimits(unittest.TestCase):
    """額度查詢跟著消耗速度走：用假時間檢查閒置、快燒、剛變慢、跨過重置。"""

    def setUp(self):
        self.m = helpers.load()
        self.db = self.m.open_ledger(":memory:")
        self.addCleanup(self.db.close)
        self.cp = self.config()

    def config(self, refresh="adaptive", minutes=10):
        cp = self.m._ini()
        cp.read_string(self.m.DEFAULT_CONFIG)
        cp.set("limits", "refresh", refresh)
        cp.set("codex", "poll_minutes", str(minutes))
        return cp

    def samples(self, points, name="5h", resets_at=T0 + 3 * 3600, window=300):
        """points：[(相對 T0 的秒數, 已用 %)]，照帳本的規則只寫有變的那幾筆。"""
        self.m.add_limits(self.db, [{"source": "codex", "name": name, "ts": T0 + dt, "used_percent": u,
                                     "window_minutes": window, "resets_at": resets_at} for dt, u in points])

    def plan(self, t, last, cp=None):
        return self.m.limit_poll_plan(self.db, "codex", last, t=t, cp=cp or self.cp)

    def test_idle_goes_back_to_the_configured_interval(self):
        self.samples([(-7200, 40)])
        p = self.plan(T0, T0 - 60)
        self.assertEqual((p["interval"], p["why"]), (600, "idle"))
        self.assertEqual(p["at"], T0 - 60 + 600)
        # 快燒過、後來停了兩小時：慢慢放鬆，最後也回到設定值
        self.samples([(-7800, 80), (-7740, 85)], name="week", window=10080, resets_at=T0 + 86400)
        self.assertEqual(self.plan(T0, T0 - 60)["interval"], 600)

    def test_fast_burn_polls_more_often(self):
        # 先慢後快：變快立刻採用（每 5 分鐘 20 % = 每分鐘 4 %）
        self.samples([(-900, 40), (-600, 40.5), (-300, 60.5)])
        p = self.plan(T0 - 300, T0 - 300)
        self.assertEqual(p["why"], "burn")
        self.assertAlmostEqual(p["interval"], 39.5 / (4 / 60.0) / 4)
        self.assertEqual(p["args"]["eta"], round(39.5 * 15))
        # 剩不多又燒很快：最短 1 分鐘
        self.samples([(0, 80), (300, 98)])
        p = self.plan(T0 + 300, T0 + 300)
        self.assertEqual((p["interval"], p["at"], p["args"]["name"]), (60, T0 + 360, "5h"))

    def test_one_step_seconds_apart_is_not_a_burst(self):
        # Codex 的 log 幾秒寫一筆：整數百分比 16 秒內跳一格，不能當成每分鐘 4 %
        self.samples([(-3600, 41), (-16, 42), (0, 43)])
        p = self.plan(T0, T0)
        self.assertEqual((p["interval"], p["why"]), (600, "calm"))

    def test_just_slowed_down_relaxes_gradually(self):
        self.samples([(0, 40), (300, 60), (600, 80)])
        fast = self.plan(T0 + 600, T0 + 600)["interval"]
        self.assertAlmostEqual(fast, 20 / (20 / 300.0) / 4)
        self.samples([(900, 82)])   # 這 5 分鐘只用了 2 %
        slowed = self.plan(T0 + 900, T0 + 900)["interval"]
        self.assertTrue(fast < slowed < 600, slowed)   # 慢慢放鬆，不會馬上跳回 10 分鐘

    def test_polls_again_30_seconds_after_a_reset(self):
        self.samples([(-3600, 70)], resets_at=T0 + 100)
        p = self.plan(T0, T0 - 10)
        self.assertEqual((p["at"], p["why"], p["args"]["name"]), (T0 + 130, "reset", "5h"))
        # 錯過了重置（電腦睡著）：馬上該查
        self.assertLessEqual(self.plan(T0 + 400, T0 - 10)["at"], T0 + 400)
        # 重置後查過了就回到一般的間隔
        p = self.plan(T0 + 140, T0 + 135)
        self.assertEqual((p["at"], p["why"]), (T0 + 735, "idle"))

    def test_fixed_mode_and_first_poll(self):
        self.samples([(0, 90), (60, 94)], resets_at=T0 + 100)
        p = self.plan(T0 + 60, T0 + 60, cp=self.config("fixed"))
        self.assertEqual((p["interval"], p["at"], p["why"]), (600, T0 + 660, "fixed"))
        self.assertEqual(self.plan(T0, None)["why"], "first")
        self.assertIsNone(self.plan(T0, T0, cp=self.config(minutes=0)))
        self.assertEqual(self.m.limits_refresh(self.config("bogus")), "adaptive")

    def test_updater_follows_the_burn(self):
        """背景更新：Codex 每分鐘燒 4 %，一看出速度就照「剩餘 ÷ 速度 ÷ 4」加快；沒資料的 Claude 照舊 10 分鐘一次。"""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        old = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(old)))
        os.environ["COMPUTAI_CONFIG_DIR"] = tmp
        m = self.m
        m.sync = lambda *a, **k: None
        m.machines = lambda: []
        m.card_settings = lambda: {"repo": ""}
        m.CLOUDS = []
        polls = {"codex": [], "claude": []}

        def codex(db):
            t = m.now()
            polls["codex"].append(t)
            m.add_limits(db, [{"source": "codex", "name": "5h", "ts": int(t), "window_minutes": 300,
                               "used_percent": 20 + 4 * (t - T0) // 60, "resets_at": T0 + 3 * 3600}],
                         only_changes=True)
        m.codex_account_poll = codex
        m.claude_account_poll = lambda db: polls["claude"].append(m.now())
        upd = m.Updater()
        for step in range(0, 15 * 60 + 1, 30):
            os.environ["COMPUTAI_FAKE_NOW"] = str(T0 + step)
            upd.tick(self.db)
        self.assertEqual(polls["claude"], [T0, T0 + 600])
        # 600 秒時用了 60 %：剩 40 % ÷ 每分鐘 4 % ÷ 4 = 150 秒；750 秒時剩 30 % → 112.5 秒（下一次 30 秒的 tick 是 870）
        self.assertEqual(polls["codex"], [T0, T0 + 600, T0 + 750, T0 + 870])


if __name__ == "__main__":
    unittest.main()
