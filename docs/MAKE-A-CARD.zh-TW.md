# 做你的第一張 ComputAI 圖卡

選範圍、選版型、下載。社群用 PNG，GitHub README 用 SVG；不用先設定 GitHub、方案或常駐服務。

**目前是 beta.2 本機開發功能，已發佈的 beta.1 尚未包含。** 以下從這份開發版資料夾執行；朋友公開下載的入口要等下一版發佈。
需要 Python 3.8+，並在使用 AI 工具的那台電腦上製作。

<img src="images/share-preview.png" width="320" alt="Web／TUI 風格的直式分享圖，使用合成示範資料">

## 已經安裝這份開發版

```sh
computai --create --lang zh
```

瀏覽器會自動開啟製卡頁。預設選最近一個有紀錄、已結束的月份；也能選本月、年份或累計歷史。
選好後按「下載 PNG」，就能把圖片貼到 Threads 或其他社群。
「複製貼文文字」附日期、精確數字和統計定義，下方的文字區也可以先修改。

## 有開發版資料夾，還沒安裝

macOS／Linux 一次安裝並開啟製卡頁，不需要重開終端機或調 PATH：

```sh
sh install.sh --create
```

Windows：

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1 -Create
```

只用 GUI 的人，可以在資料夾裡雙擊 macOS 的 `Make a card.command` 或 Windows 的 `Make a card.cmd`。
這兩個入口直接製卡，不安裝背景服務；仍需要已有 Python 3.8+。尚未提供內建 Python 的桌面安裝包。

也能直接跑 `python3 ./computai --create --lang zh`；Windows 用 `py -3 computai --create --lang zh`。

## README 卡片

製卡頁的「用途」選 **GitHub README**，選範圍和深淺色，按「下載 SVG」。
把圖檔放在 README 同一層，再貼上「複製 README 語法」取得的內容，GitHub 就會顯示卡片。
這一步是手動放圖，不需要把 ComputAI 綁到 GitHub 帳號。

之後要更多既有風格、每日自動更新或 GitHub 發佈，再看 [卡片設定](MANUAL.zh-TW.md#自動更新的-github-個人頁卡片)；
製卡頁也有折疊的進階入口，不擋住第一張圖的下載。

## 已經開著 Web 或 TUI

Web 頂端按「做我的圖卡」；TUI 按 `c`。這兩個入口讀取現有帳本，不另外同步或執行模型。
若要更新本機歷史，重新執行 `computai --create`。

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
computai --create --profile 2026-09 --html creator.html --no-sync --lang zh
computai --create --no-open --lang zh    # 只寫檔，不開瀏覽器
```

PNG 由瀏覽器以原尺寸匯出；SVG 可以縮放。若瀏覽器不允許複製，頁面會選取文字讓你按 ⌘C／Ctrl+C。
