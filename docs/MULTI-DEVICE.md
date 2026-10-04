# 多台電腦的用量合併

額度（5 小時、每週）本來就是整個帳號的，任何一台用 `claude`／`codex` 讀到的數字都一樣。
但 token 和花費來自**這台**的 log：在別台電腦用 Claude Code、Codex，用量不會進帳本。
這份文件比較兩種把別台的用量帶進來的方法，兩種都實作了，推薦 A。

## 兩條路

| | A. 共用資料夾 | B. SSH 拉取 |
|---|---|---|
| 怎麼運作 | 每台把自己的用量寫成 `<裝置代號>.jsonl` 放進大家都同步的資料夾，讀別台的檔案合併 | 對 `[machine.X] usage = pull` 的機器，SSH 進去跑 `computai --export-usage`，把輸出合併 |
| 需要 | 每台都裝 computai；一個同步資料夾（iCloud Drive、Dropbox、Syncthing、私人 git repo） | 這台能免密碼 SSH 過去；對方有 python3（3.8+） |
| 誰要開著 | 各自同步，誰開著就看得到誰最後寫的資料 | 對方要開機、連得到 |
| 適合 | 筆電、桌機、公司電腦，彼此不一定連得到 | homelab、一直開著、本來就在 `[machines]` 裡的機器 |
| 雙向 | 是：每台都看到全部 | 否：只有拉的那台看得到 |
| 隱私 | 資料只經過你自己的同步服務 | 資料只走 SSH |

**推薦 A**：大部分人的「其他電腦」是筆電和公司電腦，彼此不一定連得到，但都同步著同一個雲端資料夾；
A 也讓每台都看到全部的用量。B 留給本來就用 SSH 監看的 homelab 機器。

## 交換的內容（兩條路同一種格式）

第一行是標頭，之後每行一筆用量：

```
{"computai_export": 1, "device": "a1b2c3d4e5f6", "name": "laptop", "written": 1790000000, "version": "0.1.0", "cols": [...]}
["claude","msg_A:req_A",1790000000,"claude-opus-5-5","alpha",3,1000,0,200,377,0,1,0,"4e0f83a1276b905c"]
```

- 欄位是白名單：`source, uid, ts, model, project, input, cache_read, cache_write_5m, cache_write_1h, output, reasoning, requests, subagent, session`。
- `project` 只留資料夾名稱（`alpha`，不是 `/Users/me/work/alpha`）；原始 session id、prompt、回應、完整路徑都不會出去。
- `session` 是裝置代號、來源和原始 session id 的 JSON 陣列經 SHA-256 後取前 16 個十六進位字元。
  同一台、同一來源的同一個 session 會得到相同代號，供時間軸、同時執行數和工作時數分組；不同裝置或來源的代號不同。
  沒有 session 的原始紀錄仍送空字串，不能據此還原缺少的分組。
- 只交換 `claude` 和 `codex`。本地模型（proxy）和組織 API 的用量每台各自記，交換會重複計算；額度樣本也不交換
  （不同電腦可能登入不同帳號，各自問官方 CLI 就好）。

## 合併規則

- 帳本多一個 `device` 欄位（`''` 是這台），舊帳本開啟時自動補上；另有 `devices` 表記每台的名字、最後回報時間、經由哪條路、錯誤。
- 同一筆 `(source, uid)` 只記一次，所以同一份檔案讀兩次、或兩條路都拉到同一台，都不會重複計算；同一筆變長（串流中途寫下的半截）時取比較大的。
- 同一筆已匯入資料的 `session` 若為空，重新合併同裝置的新格式匯出檔會補上匿名代號，即使 token 數沒有增加。
  補填不會降低既有 token 數、覆蓋非空 session 或修改本機紀錄的 session。
- 自己的檔案繞回來（同一個裝置代號）就略過。
- **壞檔**：讀檔時整份檢查（JSON、欄位型別、長度、來源），任何一行不對就整份不要，記下原因給 `--doctor`。
  帳本只會新增、不會因為別台的檔案而刪資料，所以上一份好的結果一直都在，絕不清空。
- **原子寫入**：先寫 `.<檔名>.<pid>.tmp` 再改名，同步軟體和別台永遠只看到完整的舊檔或完整的新檔。

## 新不新

- 每台另外寫一個小的 `<裝置代號>.json` 當心跳（最多 1 分鐘一次）；用量檔有變才重寫（最多 2 分鐘一次）。SSH 拉取最多 5 分鐘一次。手動 `--sync` 不等。
- 超過 10 分鐘沒回報的裝置標成「過時」：總覽、網頁、`--summary`、`--doctor` 都看得到。

## B 的細節

- 對方只需要 SSH 和 python3。computai 這個檔案透過同一條 SSH（heredoc 裡的 base64）送到對方的 `~/.cache/computai/computai`，內容沒變（SHA-256 一樣）就不重送。
- 在對方執行時，設定和帳本放在 `~/.cache/computai/{config,data}`，不碰對方自己的 ComputAI。
- 游標：每次從上次寫出時間的前一天開始拉，中途變長的紀錄也會更新到。
  升級匿名 session 格式後，每個 SSH 來源會先成功拉取一次完整歷史，補填舊資料，再恢復增量；失敗時下次重試完整歷史。
- 沒有 python3、SSH 不通、輸出格式不對，都記在 `--doctor`，不影響其他來源。

## 從沒有 session 的舊格式升級

- 共用資料夾：兩台都更新後各執行 `computai --sync`。來源端會重寫完整匯出檔，即使 token 用量沒變；接收端重新合併並補填 session。
  背景同步沿用最多兩分鐘一次的寫檔節流，手動 `--sync` 不等。
- SSH：更新拉取端後執行 `computai --sync`，程式會更新遠端的快取執行檔並自動重拉完整歷史一次。
- 舊版讀新檔時忽略新增欄位；新版讀舊檔時將 session 留空。來源仍用舊版或原始 log 已刪除時，缺少的歷史 session 無法補回。
- 這是 beta.2 開發版修正；公開的 `v0.1.0-beta.1` 尚不含匿名 session 欄位。

## 設定

```ini
[devices]
folder = ~/Library/Mobile Documents/com~apple~CloudDocs/computai   # A
name = laptop                                                       # 這台在清單裡的名字（預設主機名）

[machine.m1m]
usage = pull                                                        # B
```

## 顯示

- `computai --summary`：最後多一段「Devices」，每台的請求數、token、等值花費、最後回報。
- `computai --summary --by device`：照裝置拆開。
- 總覽的「本月」卡片寫幾台、幾台過時；「AI 訂閱與花費」面板和網頁列出每台。
- 個人頁卡片只寫台數（`3 RIGS`），不寫機器名稱。
