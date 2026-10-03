"""測試共用的小工具：載入 computai 模組、在暫存目錄裡跑指令。"""

import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "computai")
FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def load():
    """每次載入一份全新的模組，模組層級的狀態不會在測試之間互相污染。"""
    loader = importlib.machinery.SourceFileLoader("computai_under_test", SCRIPT)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def fixture(*parts):
    return os.path.join(FIXTURES, *parts)


class Sandbox:
    """一個乾淨的設定檔目錄和帳本目錄，用完自動刪掉。"""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="computai-test-")
        self.config = os.path.join(self.root, "config")
        self.data = os.path.join(self.root, "data")

    def env(self, **extra):
        e = {k: v for k, v in os.environ.items() if not k.startswith("COMPUTAI_")}
        e.update(COMPUTAI_CONFIG_DIR=self.config, COMPUTAI_DATA_DIR=self.data, TZ="UTC", LANG="en_US.UTF-8",
                 PYTHONIOENCODING="utf-8", HOME=self.root, USERPROFILE=self.root,
                 CLAUDE_CONFIG_DIR=os.path.join(self.root, "no-claude"),
                 CODEX_HOME=os.path.join(self.root, "no-codex"))
        e.update({k: str(v) for k, v in extra.items()})
        return e

    def run(self, *args, timeout=60, **extra):
        return subprocess.run([sys.executable, SCRIPT, *args], env=self.env(**extra),
                              capture_output=True, text=True, encoding="utf-8", timeout=timeout)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)
