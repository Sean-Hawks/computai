# ComputAI 路線圖（2026-10，公測之後）

每一項都是一則可以直接交給 coding agent 的 prompt：目標、限制、驗收條件都寫在裡面。
一次做一項，每項開一個分支。

建議順序：**1 → 4 → 2**（把公測做紮實），接著 **5、7**（別的工具沒有的差異點），
**6、8、9** 適合搭配 Wrapped 和社群宣傳，**10** 隨時可以穿插。

| # | 項目 | 類型 | 大小 |
|---|---|---|---|
| 1 | 額度查詢跟著消耗速度走 | 公測 | 小 |
| 2 | 多台電腦的用量合併 | 公測 | 大 |
| 3 | 從別台電腦打開網頁版（`--web --tailscale`） | 公測 | 小 |
| 4 | 第一次打開就有感 | 公測 | 中 |
| 5 | `computai --pick`：讓額度決定用哪個 agent | 跳脫思維 | 中 |
| 6 | agent 時間軸 | 跳脫思維 | 中 |
| 7 | 額度護欄（hook） | 跳脫思維 | 中 |
| 8 | 本地模型的真實成本和分流建議 | 跳脫思維 | 中 |
| 9 | 朋友之間的排行榜（只交換總數） | 跳脫思維 | 中 |
| 10 | 更多來源，以及網頁版跟上 TUI | 擴充 | 大 |

---

## 共用開頭（每一項前面都要帶）

```
你在 ~/Documents/computai 工作。開始前先讀 CLAUDE.md、GOAL.md、docs/RESEARCH.md、docs/DESIGN.md，
以及 NIGHT_LOG.md（只存在本機）。
遵守 CLAUDE.md：單一 Python 檔、只用標準函式庫、支援 3.8+；被監控的節點只需要 SSH 和 POSIX sh；
不讀、不存 prompt 和回應的內容；不碰 ~/.codex/auth.json 和 Claude 的 OAuth token；網頁和 proxy 預設只聽 127.0.0.1。
每個里程碑開一個分支，小步 commit（英文祈使句），每個資料來源都要有 fixture 測試，
tests/run.sh 在 3.14 和 3.8 都要過。做完在 NIGHT_LOG.md 補交接，合併到 main 並 push。
```

---

## 1. 額度查詢跟著消耗速度走

現在 Claude（`claude -p /usage`）和 Codex（`codex app-server`）的帳號額度固定每 10 分鐘查一次。
問題有兩個：重置後最多要等 10 分鐘才會顯示恢復；剩 10% 又燒很快時，畫面上的數字可能已經過時。
（點子來自 token-monitor 的 `limits/burnRate.js` 和 `resetBoundary.js`，只參考做法。）

改成自適應查詢：

- 間隔 = 剩餘 % ÷ 觀察到的消耗速度 ÷ 4，最短 1 分鐘、最長是設定值（預設 10 分鐘）。閒置時速度是 0，回到設定值。
- 消耗變快立刻採用；變慢只用權重 0.3 慢慢放鬆，不要剛停下來就馬上回到慢速。
- 任何視窗的重置時間一到，過 30 秒就多查一次。
- 消耗速度從帳本 `limits` 表裡同一個視窗的連續樣本算，不要另外存狀態。
- 加 `[limits] refresh = adaptive|fixed`，預設 `adaptive`。

驗收：

- 用假時間的單元測試涵蓋四種情況：閒置、快燒、剛變慢、跨過重置。
- `--doctor` 顯示每個來源的下次查詢時間和原因（例如「Codex 每週照速度 3 小時後用完 → 每 1 分鐘」）。

## 2. 多台電腦的用量合併到同一本帳

額度已經是整個帳號的，但 token 和花費只算到跑 computai 的那台；在其他機器上用 Claude、Codex 的用量沒有進帳本。

先寫設計文件 `docs/MULTI-DEVICE.md` 比較兩條路，再實作推薦的那條（也可以兩條都做）：

- **A. 共用資料夾快照**：
  - 每台跑 computai 的機器，把自己的用量列（只有用量欄位，加上 device id）寫成一個 JSONL 檔，
    放進使用者指定的資料夾（iCloud、Dropbox、Syncthing、私人 git repo 都行）。
  - 每台讀取時合併、去重。
  - 寫入要原子化；檔案壞掉或缺漏時保留上一份好的結果，絕不清空。
- **B. SSH 拉取**：
  - 對 `[machines]` 裡的機器，把 computai 這個單一檔案 scp 到遠端的快取目錄。
  - 在遠端執行 `computai --export-usage --since <游標>`，只回傳用量欄位，拉回來合併。
  - 遠端只需要 python3，沒有就略過並說明。

要求：

- 帳本加 `device` 欄位（要有遷移）。
- 總覽、`--summary`、卡片可以照機器分組；超過 10 分鐘沒更新的裝置標成 stale。
- 隱私測試：fixture 裡放假的 prompt 文字，驗證合併後的帳本裡完全沒有。

## 3. 從別台電腦打開網頁版（`--web --tailscale`）

網頁仍然只聽 `127.0.0.1`，改由 Tailscale 安全地轉出去：

- `computai --web --tailscale`：
  - 偵測 tailscale CLI，執行 `tailscale serve --bg <port>`，印出可以直接點的 `https://<機器>.<tailnet>.ts.net` 網址。
  - 結束時（包含 Ctrl-C）自動關掉 serve。
- 沒有 Tailscale 時說明怎麼裝，不要退回 `0.0.0.0`。
- `--install-watch` 也可以帶這個選項，讓背景服務常駐在 tailnet 上。
- Cloudflare Tunnel 當進階選項：只有在設好 Cloudflare Access 時才允許開，否則拒絕並說明原因。先寫進文件，不用實作。

驗收：用假的 tailscale 執行檔寫測試，涵蓋開啟、關閉、找不到程式三種情況。

## 4. 公測準備：第一次打開就有感

目標：完全沒設定過的人跑完一行安裝後打 `computai`，10 秒內就看到有意義的畫面。

- 從乾淨的 HOME 走一遍（沒有設定檔、沒有機器、沒有方案），列出每個卡住或看不懂的地方，逐一修掉。
  例如「沒有額度」時說明怎麼接；「沒有方案」時根據 log 猜方案，問一句就好。
- 加 `.github/ISSUE_TEMPLATE`：bug 回報要附 `computai --doctor --redact` 的輸出。
  `--redact` 會把機器名、IP、專案名換成代號。
- 加更新檢查：一天最多一次，可以關閉。
- 準備 `v0.1.0-beta` 的 release notes（先不要發佈，等作者確認）。
- 用 Docker 的 `python:3.8-slim` 和 `ubuntu` 各跑一次安裝和測試，確認 Linux 沒問題。
- 重截 `docs/images/web.png`，換成現在的配色。

---

## 5. `computai --pick`：讓額度決定用哪個 agent

ComputAI 知道每個額度還剩多少、多久重置、本地模型有沒有空。把它從「看的工具」變成「決定的工具」：

- `computai --pick [--task light|heavy]` 印出現在最適合的工具（`claude`、`codex`、`local:<模型>`），以及一行理由。
- 規則：
  - 優先用快要重置而且還沒用完的額度，因為重置後就浪費了。
  - 避開照目前速度會提早用完的額度。
  - 輕量任務優先用本地模型。
- 給 shell 用：`$(computai --pick) "幫我整理這個 PR"`；`--json` 給腳本用。
- MCP 也加同名的 tool，讓 agent 自己問「這個子任務該丟給誰」。
- 首頁「需要處理」加一類建議，例如：「Claude 5 小時額度 40 分鐘後重置、還剩 60%，現在用最划算」。

驗收：規則表寫成可以測試的純函式，用各種額度組合做表格驅動測試。

## 6. agent 時間軸：今天我的 agent 在做什麼

只用帳本裡的時間戳和 token 數（不碰內容），在 TUI 加一個「時間軸」分頁：

- 畫成甘特圖：
  - 每一列是一個 session（Claude、Codex、本地模型、哪台機器），橫軸是今天的時間。
  - 方塊的濃淡代表 token 密度，subagent 縮排在主 session 底下。
- 標出三種時刻：同時跑最多 agent 的時候、最長的連續工作、空等的時間（session 開著但很久沒有請求）。
- 一行總結，例如：「今天 agent 替你工作 6.2 小時，最多 4 個同時，花最多的是下午 2 點那一段」。
- 同一份資料輸出成 SVG，可以放進 Wrapped 和個人頁卡片。

驗收：fixture 涵蓋跨午夜、subagent、多台機器的情況；60 欄的窄終端機也要能看。

## 7. 額度護欄：agent 自己會踩煞車

寫一個可選的 Claude Code hook（Codex 有對應機制的話也做），讓 agent 在額度或預算快用完時自己知道：

- `computai --hook claude-stop` 和 `--hook claude-pretool`：
  - 只讀帳本，不呼叫網路，50ms 內回應。
  - 額度剩不到 N%，或本月預算超標時，輸出提醒。
  - 設成 strict 的話，大型操作（例如一次派出很多 subagent）會被擋下來，並說明原因。
- `computai --setup` 問要不要裝；裝之前先用 diff 顯示 `settings.json` 會怎麼改。
- 只輸出 hook 規定的 JSON；hook 本身出錯時一律放行，絕不卡住使用者。

驗收：用假的 hook 輸入做測試，涵蓋四種情況：正常、快用完、超標、帳本讀不到。

## 8. 本地模型的真實成本和分流建議

ComputAI 同時知道電費、功耗、tok/s 和 API 價格。做一份「什麼該丟本地、什麼該丟雲端」的報告：

- 每個本地模型：
  - 每 100 萬 token 的電費。
  - 跟 claude-haiku、gpt-mini 比的打平點。
  - 機器折舊選填（`[local] hardware_usd`、壽命年數）。
- 用 `--bench` 的歷史加上實際用量，算「如果這個月的輕量請求都走本地，可以省多少額度和錢」。
- 也算碳排放（`[energy] grid_kg_per_kwh`；台灣的預設值要附來源和查詢日期）。
- 放進「本地模型」分頁和 Wrapped，例如：「這個月本地模型替你省了 $17，花了 0.6 度電」。

## 9. 朋友之間的排行榜（只交換總數）

做一個完全選擇加入的「小隊」功能，不需要伺服器：

- `computai --team publish`：
  - 把「只有總數」的 JSON 推到一個共用位置（GitHub Gist 或私人 repo）。
  - 內容只有 tokens、agent 小時、最多同時幾個、連續天數，不含專案名稱和機器名稱。
- `computai --team` 在 TUI 顯示排行榜和每週變化；Wrapped 加一頁「小隊」。
- 發佈前先顯示完整的 JSON 讓使用者確認；可以隨時用 `--team leave` 撤回。

驗收：測試驗證發佈內容裡不會出現專案名、路徑、機器名、IP。

## 10. 更多來源，以及網頁版跟上 TUI

- **(a) 更多來源**：
  - 參考 [token-monitor](https://github.com/Javis603/token-monitor) README 的工具路徑表（MIT，只參考路徑和格式，不抄程式碼）。
  - 依使用人數挑 3 個來源加進來，建議 OpenCode、Gemini CLI、Cursor（帳號匯出檔）。
  - 每個都要有去除內容的 fixture，parser 只取用量欄位。
- **(b) 網頁版改成跟 TUI 首頁一樣的版面**：
  - 額度橫幅、四塊數字卡、機器表、需要處理。
  - 可以用真的圓角、甜甜圈和折線。
  - 資料走同一份 `dashboard_state()`，網頁和 TUI 不能各說各話。
  - 手機寬度要能看；加上 manifest，用 Tailscale 打開就能「加到主畫面」當 App。

---

## 研究筆記：token-monitor 值得參考、不該學的

- **值得參考**：
  - 依「多久會用完」決定查詢間隔（第 1 項）。
  - 每台裝置只送摘要、讀取時才彙總；壞檔保留上一份好的結果（第 2 項）。
  - 超過 10 分鐘沒回報的裝置標成 stale。
  - 訂閱續約日和回本倍數。
  - 服務狀態頁（Anthropic、OpenAI 出事時放進「需要處理」）。
  - CSV 匯出。
- **不該學**：
  - 它會讀 `~/.claude/.credentials.json` 和 Keychain 裡的 OAuth token，再自己呼叫 usage API。這違反 ComputAI 的隱私原則；
    我們用 `claude -p /usage` 的結構化輸出就拿得到同樣的數字。
  - 它的 Claude CLI 備案是開假終端機打 `/usage`，再用正規表達式抓螢幕文字，不穩。
  - 用量歷史封存：ComputAI 的 SQLite 帳本本來就永久保存，不需要另外做。
