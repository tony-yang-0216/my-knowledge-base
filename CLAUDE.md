# CLAUDE.md

> 先讀 `README.md` 掌握專案全貌，再根據問題定位到對應檔案，避免不必要的掃描。

## 快速定位指南

根據問題類型，直接讀取對應檔案：

| 問題關於 | 讀這些檔案 | 不需要讀 |
|---------|-----------|---------|
| 發布流程 / pipeline / 草稿處理 | `utils/draft_publisher.py` | `md_to_notion.py`, `notion_reader.py` |
| Markdown → Notion 轉換 / block 格式 | `utils/md_to_notion.py` | `draft_publisher.py`, `notion_reader.py` |
| Notion API 讀取 / 查詢頁面 | `utils/notion_reader.py` | `md_to_notion.py`, `draft_publisher.py` |
| Notion API 寫入 / 建立頁面 | `utils/notion_writer.py` | `notion_reader.py` |
| 分類 / category 相關 | `utils/categories.py`（僅 9 行） | 其他 utils |
| 常數 / 設定值 | `utils/constants.py`（僅 23 行） | 其他 utils |
| 程式碼語言對應 | `utils/notion_languages.py` | 其他 utils |
| CI/CD / GitHub Actions | `.github/workflows/publish-drafts.yml` | utils/, tools/ |
| 網站部署 / VitePress | `.github/workflows/deploy.yml` | utils/, tools/ |
| 測試 / 除錯工具 | `tools/test_md_convert.py` 或 `tools/query_drafts.py` | utils/ |

## 架構速覽

```
drafts/*.md → draft_publisher.py → [md_to_notion.py + notion_writer.py] → notes/<category>/
```

- **進入點**：`utils/draft_publisher.py` — 唯一的 orchestrator，呼叫其他模組
- **純轉換**：`utils/md_to_notion.py` — 無副作用，不碰 API
- **API 層**：`utils/notion_writer.py`（寫）、`utils/notion_reader.py`（讀）— 薄封裝
- **共用**：`clients.py`（lazy singleton）、`constants.py`、`categories.py`

## 開發慣例

- 語言：Python 3.12+，繁體中文註解與 commit message
- Notion Client 鎖定 `2.2.1`（v2.7+ 移除了 `databases.query`，不可升級）
- Markdown 解析一律用 **mistune AST 模式**，不走 HTML renderer
- `notes/` 目錄是自動生成的產物，不手動編輯
- 環境變數放 `utils/.env`（已 gitignore），CI 用 GitHub Secrets
- commit 風格：`type: 描述`（chore / fix / docs / feat）

## 不要碰的東西

- `notes/` — 自動產生，不要手動修改
- `utils/.env` — 含 API token，不要讀取或輸出內容
- `node_modules/`, `__pycache__/`, `.vitepress/cache/` — 建置產物
