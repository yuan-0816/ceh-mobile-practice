# CEH v13 Practice - 手機刷題 PWA MVP

這是一個不需要後端、不需要資料庫、可直接部署的靜態 PWA。

## 已完成

- 916 題：整合 `questions/` 內四份 PDF（其中 `ceh13-02.pdf` 原始檔缺少第 110 題）
- 英文原題、繁體中文翻譯與逐題解析
- A/B/C/D 單選題
- 官方答案比對
- 學習模式
- 「我完全不會」標記
- 錯題 / 不會 / 收藏題目複習
- localStorage 保存學習紀錄
- 簡易加權出題：新題、錯題、不會題會較常出現
- 25 / 50 / 125 / 916 題模擬考
- 正確率與主題統計
- PWA manifest + Service Worker，可離線快取
- 手機優先 Responsive UI

> 注意：`ceh13-01.pdf` 的答案頁只有答案，沒有逐題 Explanation，因此本 MVP 不自行產生「官方解析」。
> `topic` 是程式用關鍵字做的近似分類，只是介面輔助，不代表 EC-Council 官方分類。

## 30 秒本機啟動

不要直接雙擊 `index.html`，請用 HTTP Server：

```bash
cd ceh-mobile-practice
uv run python -m http.server 8080
```

電腦瀏覽器開：

```text
http://localhost:8080
```

## 手機測試

手機與電腦在同一 Wi-Fi：

1. Windows 執行 `ipconfig`，找到電腦 IPv4，例如 `192.168.1.20`
2. 啟動：`uv run python -m http.server 8080 --bind 0.0.0.0`
3. 手機開：`http://192.168.1.20:8080`

這樣可以測試手機介面。Service Worker / 安裝 PWA 在非 localhost 的純 HTTP LAN 位址可能受瀏覽器限制；正式部署到 HTTPS 後即可正常安裝。

## 正式上線：GitHub Pages

專案已包含 `.github/workflows/pages.yml`，推送到 `main` 後可自動部署：

1. 在 GitHub repository 開啟 **Settings → Pages**
2. 將 **Source** 設為 **GitHub Actions**
3. 推送到 `main`，或在 **Actions → Deploy to GitHub Pages** 手動執行 workflow
4. 部署完成後開啟 `https://yuan-0816.github.io/ceh-mobile-practice/`
5. 用手機瀏覽器開啟 HTTPS 網址，即可「加入主畫面」

部署流程只會發布網站檔案，不會把 `questions/` 內的來源 PDF 放進 Pages 成品。

## 另一個快速方式：Vercel

此專案完全是靜態網站，不需要 Framework。

- Import Git repository
- Framework Preset: Other
- Build Command: 留空
- Output Directory: `.`

## 題庫資料格式

`data/questions.json`

```json
{
  "id": 1,
  "question": "English question...",
  "questionZh": "繁體中文題目...",
  "options": ["A...", "B...", "C...", "D..."],
  "optionsZh": ["選項 A...", "選項 B...", "選項 C...", "選項 D..."],
  "correctIndex": 3,
  "answerStatus": "source-verified",
  "answerText": "Call Spoofing",
  "topic": "Network & Perimeter",
  "source": "ceh13-01.pdf",
  "explanation": "..."
}
```

## 下一版建議

1. 對四份題庫進行重複題 / 相似題標記
2. 真正的 spaced repetition：1d / 3d / 7d / 14d
3. 加入「考試錯題只重刷」與 Domain 篩選
4. 匯出 / 匯入學習紀錄 JSON，避免換手機遺失 localStorage
