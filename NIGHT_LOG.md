# NIGHT_LOG

每個里程碑做完在這裡補一段交接。最新的在最下面。

## 分支的做法

每個里程碑一個分支（`m1-skeleton`、`m2-subscriptions`……），做完在本機 fast-forward 合進 `main`，
下一個里程碑從 `main` 開。全部都沒有 push。

## M1 骨架（分支 `m1-skeleton`）

**做了什麼**
- 單一檔案 `computai`（Python 3.8+，只用標準函式庫）。
- 設定檔目錄 `~/.config/computai/`（`COMPUTAI_CONFIG_DIR`、`XDG_CONFIG_HOME`，Windows 用 `%APPDATA%`）：
  第一次執行時寫入 `config.ini`（方案月費）和 `prices.ini`（API 價目表）；之後只讀檔案，使用者改的會保留。
- 金鑰只從環境變數或權限 600 的 `secrets.ini` 讀；權限太寬會警告並忽略。
- 帳本 `~/.local/share/computai/ledger.sqlite`（`COMPUTAI_DATA_DIR`、`XDG_DATA_HOME`，Windows 用
  `%LOCALAPPDATA%`）。`usage` 以 `(source, uid)` 當主鍵，`INSERT OR IGNORE`，所以重複匯入不會重複計算。
  `files` 表記錄每個 log 檔的大小和修改時間，沒變的檔案不會重讀。
- 指令：`--sync`、`--summary`、`--month [YYYY-MM]`、`--since`、`--until`、`--json`、`--paths`、`--no-sync`。
  `--summary` 預設會先自動同步一次。
- 花費在查詢時才用價目表換算，所以改價格會立刻反映到舊資料。
- 測試：`tests/run.sh` 會用 python3 和 Python 3.8（uv 裝的）各跑一次。

**替你做的決定**
- 設定檔用 INI（`configparser`）：3.8 沒有 `tomllib`，JSON 又不能寫註解。
- token 欄位統一成 Anthropic 的語意：`input` 是「沒命中快取的輸入」，OpenAI 的資料匯入時先扣掉 cached。
  `output` 含 reasoning，`reasoning` 只是細項。
- 非整月的範圍，方案月費按天數比例攤（30.44 天一個月）。

**還沒實機驗證**
- Windows 路徑（`%APPDATA%`、`%LOCALAPPDATA%`）只有程式邏輯，沒在 Windows 上跑過。
