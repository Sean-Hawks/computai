# 做你的第一份 ComputAI 月報

在使用 AI 工具的電腦執行 `computai recap`，打開後按「下載 PNG」，就能分享你的月報。
程式會自動找支援的本機用量、選好月份和直式版型；不用先設定模型、方案、GitHub 或常駐服務。

**這項功能自 beta.3 提供。** 可下載公開版本，或用下方的一行指令安裝並開啟月報。
需要 Python 3.8+，並在使用 AI 工具的那台電腦上製作。

<img src="images/share-preview.png" width="320" alt="Web／TUI 風格的直式分享圖，使用合成示範資料">

## 已經安裝 beta.3

只記得 `computai` 也可以：執行後選「2 做月報圖卡」，就會開相同的月報頁。
選單列有即時監控、網頁、花費分析、資料檢查與設定，不用先記參數。

```sh
computai recap
```

終端機會顯示找到的用量來源、預設月份和下一步，接著自動開啟月報頁。
預設選最近一個有紀錄、已結束的月份；也能在頁面選本月、年份或累計歷史。
選好後按「下載 PNG」，就能把圖片貼到 Threads 或其他社群。
「複製貼文文字」附日期、精確數字和統計定義，下方的文字區也可以先修改。

要指定月份，只需 `computai recap 2026-09`；需要繁中時加 `--lang zh`。
`computai recap --help` 只列月報相關選項。

## 還沒下載

macOS／Linux 可用一行安裝並打開月報：

```sh
curl -fsSL https://raw.githubusercontent.com/Sean-Hawks/computai/v0.1.0-beta.3/install.sh | sh -s -- --recap
```

Windows 從 [beta.3 版本頁](https://github.com/Sean-Hawks/computai/releases/tag/v0.1.0-beta.3)
下載並解壓 ZIP，雙擊 `Make a card.cmd` 即可開月報，不需先設定 PATH。

## 有版本資料夾，還沒安裝

在下載並解壓的 **beta.3 資料夾**開啟終端機。macOS／Linux 用一行完成安裝並打開月報，不需要重開終端機或調 PATH：

```sh
sh install.sh --recap
```

Windows：

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1 -Recap
```

只用 GUI 的人，可以在資料夾裡雙擊 macOS 的 `Make a card.command` 或 Windows 的 `Make a card.cmd`。
這兩個入口使用相同的月報流程，不安裝背景服務；仍需要已有 Python 3.8+。尚未提供內建 Python 的桌面安裝包。

也能直接跑 `python3 ./computai recap --lang zh`；Windows 用 `py -3 computai recap --lang zh`。

## 月報先確認什麼

製卡頁會列出**選定月份**各來源的首末紀錄日期、紀錄筆數和上月 token 處理量比較。
筆數不是請求數，日期有涵蓋整個月也不代表帳號用量全部收齊。
上月比較只使用緊鄰的曆月；沒有上月資料就顯示「—」，本月尚未結束或歷史不完整會附註。
本月／上月沒有用量時，選單會標明「尚無紀錄」，並停用下載，避免製作假的零用量月報。

「檢查我的資料來源」可選你的使用方式。這只檢查缺少哪些來源，**不會過濾月報總數**，也不要求先設定。

| 使用方式 | 第一版月報能用什麼 | 缺資料時 |
|---|---|---|
| Codex GUI／T3 Code | GUI 留下的支援 Codex session 用量；月份、模型、快取、輸出、活躍日 | 在同一台電腦執行 `computai recap`，再用 `--doctor` 檢查 log 路徑 |
| 本地模型 | 帳本已記錄的 local token；與 GUI 用量一起比較 | 檢查 metrics／proxy 是否開始記錄；沒有紀錄的過去無法補算 |
| 本地模型＋月費 AI 工具 | 已記錄的 local 與支援 GUI／CLI 用量來源，放在同一張月報 | 缺少的來源會提示；月費不會被當成歷史付款或 token 用量 |

第一版不涵蓋只有網頁聊天紀錄的使用者。來源代表紀錄格式，不能用來辨認究竟用了哪個 GUI。
本地設備的 GPU 時數、耗電與費用仍在原本的 `--report`；這份社群月報聚焦可記錄的 token 與活動。

需要帶走資料時，展開「帶走這個區間的彙總資料」，下載 JSON。
只包含選定區間的 token 分桶、活躍日、前五模型、來源日期與筆數，不含專案、機器、session、對話或帳單；
不會帶出其他月份，也不會上傳。累計／年報同樣只匯出所選區間。

## README 卡片

製卡頁的「用途」選 **GitHub README**，選範圍和深淺色，按「下載 SVG」。
把圖檔放在 README 同一層，再貼上「複製 README 語法」取得的內容，GitHub 就會顯示卡片。
這一步是手動放圖，不需要把 ComputAI 綁到 GitHub 帳號。

之後要更多既有風格、每日自動更新或 GitHub 發佈，再看 [卡片設定](MANUAL.zh-TW.md#自動更新的-github-個人頁卡片)；
製卡頁也有折疊的進階入口，不擋住第一張圖的下載。

## 已經開著 Web 或 TUI

Web 頂端按「做我的圖卡」；TUI 按 `c`。這兩個入口讀取現有帳本，不另外同步或執行模型。
若要更新本機歷史，重新執行 `computai recap`。

## 沒有看到自己的用量

GUI 必須留下 ComputAI 支援的本機 usage log。T3／Codex GUI 若留下 Codex session 用量，會記在 Codex 來源；
Claude GUI 若留下支援的 Claude Code 用量紀錄，會記在 Claude 來源。不根據來源推測你用了哪個 GUI。
一般聊天網站或沒有留下支援紀錄的 GUI，無法還原未記錄的用量。

`computai --doctor` 可以檢查資料來源；Cursor 要先匯入用量 CSV。本地模型只能顯示已有的帳本紀錄，製卡不會觸發推論。
空帳本會顯示說明並停用下載，不用假數字填卡片。

## 資料留在本機

只匯入本機用量欄位，不取用對話內容，不讀 auth／OAuth token，不呼叫 API、SSH 或模型。
圖卡只有選定區間的彙總，不含專案、機器、session；名稱是選填。
B＝十億，快取重複讀取計入處理量，reasoning 已含 output。token 多不代表工作能力、成果或實際付費。

製卡頁 HTML 內含可選月份的彙總，是私人工具。**請分享下載的 PNG／SVG，不分享製卡頁 HTML。**
頁面預設儲存在 ComputAI 的資料目錄，POSIX 權限為 600。製卡與下載都不會自動發文或 push。

要指定檔案、月份或只讀帳本：

```sh
computai recap 2026-09 --html creator.html --no-sync --lang zh
computai recap --no-open --lang zh    # 只寫檔，不開瀏覽器
```

舊的 `--create`／`--profile` 指令仍可使用；`--recap YEAR` 仍是原有年報，與新的 `recap` 命令不同。

PNG 由瀏覽器以原尺寸匯出；SVG 可以縮放。若瀏覽器不允許複製，頁面會選取文字讓你按 ⌘C／Ctrl+C。
