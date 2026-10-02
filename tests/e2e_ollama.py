#!/usr/bin/env python3
"""端對端測試：在這台機器上起一個 ollama，把它當成 homelab 的一台機器來監看。

    python3 tests/e2e_ollama.py [--model qwen3:0.6b] [--requests 8]

1. 在隨機的埠起 `ollama serve`（不影響你平常的 ollama）。
2. 起 `computai --proxy`，透過它送幾種請求（原生 API、OpenAI 相容 API、串流和非串流），
   腳本自己從回應裡加總 token 數。
3. 比對帳本裡 proxy 記到的 token 數，必須跟腳本自己算的一樣。
4. 模型留在記憶體裡、不再送請求，持續取樣，確認「閒置佔卡」警示會出現。
5. 不管成功失敗，最後都把 proxy 和 ollama 關掉。

不是 unittest 的一部分（要真的跑模型），檔名故意不叫 test_*.py。
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "computai")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_http(url, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(0.3)
    return False


def post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.headers.get("Content-Type", ""), r.read().decode()


def tokens_from_response(ctype, text):
    """測試腳本自己算 token：不經過 computai 的程式碼。"""
    if "event-stream" in ctype:
        for line in text.splitlines():
            if line.startswith("data:") and '"usage"' in line:
                u = json.loads(line[5:])["usage"]
                if u:
                    return u["prompt_tokens"], u["completion_tokens"]
        return 0, 0
    if "ndjson" in ctype:
        last = json.loads(text.strip().splitlines()[-1])
        return last["prompt_eval_count"], last["eval_count"]
    d = json.loads(text)
    if "usage" in d:
        return d["usage"]["prompt_tokens"], d["usage"]["completion_tokens"]
    return d["prompt_eval_count"], d["eval_count"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:0.6b")
    ap.add_argument("--requests", type=int, default=8)
    args = ap.parse_args()
    if not shutil.which("ollama"):
        print("SKIP: ollama is not installed")
        return 0

    work = tempfile.mkdtemp(prefix="computai-e2e-")
    oport, pport = free_port(), free_port()
    env = dict(os.environ, COMPUTAI_CONFIG_DIR=os.path.join(work, "config"),
               COMPUTAI_DATA_DIR=os.path.join(work, "data"),
               CLAUDE_CONFIG_DIR=os.path.join(work, "none"), CODEX_HOME=os.path.join(work, "none"))
    os.makedirs(env["COMPUTAI_CONFIG_DIR"])
    with open(os.path.join(env["COMPUTAI_CONFIG_DIR"], "config.ini"), "w") as f:
        f.write("[machines]\nsim = local\n\n[machine.sim]\nservices = ollama:%d\n"
                "idle_watts = 6\nmax_watts = 30\n\n[power]\nprice_per_kwh = 0.15\ncurrency = USD\n"
                "idle_alert_minutes = 0.1\n" % oport)

    procs = []
    ok = True
    try:
        ollama = subprocess.Popen(["ollama", "serve"], env=dict(os.environ, OLLAMA_HOST="127.0.0.1:%d" % oport),
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(ollama)
        if not wait_http("http://127.0.0.1:%d/api/version" % oport):
            print("FAIL: ollama did not start")
            return 1
        proxy = subprocess.Popen([sys.executable, SCRIPT, "--proxy", "--listen", str(pport),
                                  "--upstream", "http://127.0.0.1:%d" % oport, "--machine", "sim",
                                  "--sample-every", "2"], env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        procs.append(proxy)
        if not wait_http("http://127.0.0.1:%d/api/version" % pport):
            print("FAIL: proxy did not start")
            return 1

        base = "http://127.0.0.1:%d" % pport
        kinds = [
            ("/api/generate", lambda i: {"model": args.model, "prompt": "Count to %d." % (i + 2),
                                         "stream": False, "keep_alive": "10m",
                                         "options": {"num_predict": 24}}),
            ("/api/chat", lambda i: {"model": args.model, "keep_alive": "10m",
                                     "messages": [{"role": "user", "content": "Name %d fruits." % (i + 1)}],
                                     "options": {"num_predict": 24}}),
            ("/v1/chat/completions", lambda i: {"model": args.model, "stream": True, "max_tokens": 24,
                                                "messages": [{"role": "user", "content": "Say hi %d" % i}]}),
            ("/v1/chat/completions", lambda i: {"model": args.model, "max_tokens": 24,
                                                "messages": [{"role": "user", "content": "Say bye %d" % i}]}),
        ]
        want_in = want_out = 0
        for i in range(args.requests):
            path, body = kinds[i % len(kinds)]
            ctype, text = post(base + path, body(i))
            pi, po = tokens_from_response(ctype, text)
            want_in += pi
            want_out += po
            print("  %-22s prompt %3d  output %3d" % (path, pi, po))
        time.sleep(2.5)  # 讓 proxy 的取樣執行緒至少看到一次活動

        r = subprocess.run([sys.executable, SCRIPT, "--summary", "--json", "--no-sync"], env=env,
                           capture_output=True, text=True, timeout=60)
        s = json.loads(r.stdout)
        local = [x for x in s["sources"] if x["source"] == "local"]
        got_in = local[0]["totals"]["input"] + local[0]["totals"]["cache_read"] if local else 0
        got_out = local[0]["totals"]["output"] if local else 0
        got_n = local[0]["totals"]["requests"] if local else 0
        print("script counted: %d requests, %d prompt, %d output" % (args.requests, want_in, want_out))
        print("proxy recorded: %d requests, %d prompt, %d output" % (got_n, got_in, got_out))
        if (got_n, got_in, got_out) != (args.requests, want_in, want_out):
            print("FAIL: token counts differ")
            ok = False

        # 不再送請求，模型還留在記憶體裡：proxy 每 2 秒取樣一次，閒置門檻是 6 秒
        time.sleep(10)
        r = subprocess.run([sys.executable, SCRIPT, "--summary", "--json", "--no-sync"], env=env,
                           capture_output=True, text=True, timeout=60)
        s = json.loads(r.stdout)
        alerts = [a for a in s["alerts"] if a["kind"] == "idle_model" and a["machine"] == "sim"]
        print("alerts:", [a["message"] for a in s["alerts"]])
        if not alerts:
            print("FAIL: no idle-model alert")
            ok = False
        m = [x for x in s["machines"] if x["machine"] == "sim"]
        if m:
            print("machine sim: %.1f h sampled, %.6f kWh, AI share %s, J/token %s"
                  % (m[0]["covered_hours"], m[0]["kwh"], m[0]["ai_share"], m[0]["j_per_token"]))
        if not m or not m[0]["ai_share"]:
            print("FAIL: no AI activity seen in the samples")
            ok = False
    finally:
        for p in reversed(procs):
            p.terminate()
        for p in procs:
            try:
                p.wait(timeout=15)
            except subprocess.TimeoutExpired:
                p.kill()
        shutil.rmtree(work, ignore_errors=True)
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
