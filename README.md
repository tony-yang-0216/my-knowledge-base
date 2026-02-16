# My Knowledge Base

一套自動化的個人知識管理系統，將 AI 對話中產生的學習筆記，透過 Markdown 草稿自動同步至 Notion 資料庫，並部署為靜態網站。

## 核心流程

```
Claude.ai 對話 → /summary 生成 Markdown → drafts/ → Notion (Draft)
                                            ↓
                                    notes/<category>/*.md → Notion (Processed)
                                            ↓
                                    VitePress → GitHub Pages
```

## 草稿從哪裡來？

本專案的知識來源是與 **Claude.ai** 的深度對話。在學習任何主題時，透過不斷提問、追問、釐清概念的過程，Claude 會成為你的即時導師。

當一段對話累積了足夠的知識密度後，使用預先定義在 Claude.ai Project 中的 **`/summary` 指令**，Claude 會將整段對話濃縮為一份結構化的 Markdown 筆記。這份筆記包含：

- **YAML Frontmatter**：標題、分類、標籤等 metadata
- **目錄**：自動生成的章節導航
- **結構化內容**：定義、核心原理、實作範例、最佳實踐等
- **程式碼區塊**：含語言標記的範例程式碼
- **Mermaid 流程圖**：視覺化的概念架構圖

> `/summary` 是在 Claude.ai 的 Project Instructions 中自定義的指令，可以根據個人需求調整輸出格式、語言風格、章節結構等，產出高度客製化的學習筆記。

將生成的 Markdown 檔案複製到 `drafts/` 目錄，推送至 GitHub 後，自動化流程就會接手。

### 草稿格式範例

```markdown
---
title: "HTTP Session 管理機制：深度解析與安全實踐"
category: "10-Computer-Science"
tags: "HTTP, Session, Cookie, 資安"
---

# HTTP Session 管理機制：深度解析與安全實踐

## 目錄
- [1. 定義](#1-定義)
- [2. 核心原理](#2-核心原理)
...

## 1. 定義

HTTP Session 是一種伺服器端的狀態管理機制...
```

**必要欄位：**

| 欄位 | 說明 | 範例 |
|------|------|------|
| `title` | 筆記標題 | `"LLM Token 優化策略"` |
| `category` | 分類代碼（見下方分類表） | `"12-AI-ML"` |
| `tags` | 逗號分隔的標籤 | `"LLM, Token, 優化"` |

## 自動化發布流程

GitHub Actions 每小時自動執行以下步驟：

### 1. 掃描草稿

偵測 `drafts/` 目錄中的所有 `.md` 檔案，解析 YAML frontmatter 取得 metadata。

### 2. 建立 Notion 頁面

- 透過 **mistune** 將 Markdown 解析為 AST
- 轉換為 Notion Block 格式（標題、段落、程式碼、表格、清單、Mermaid 圖等）
- 呼叫 Notion API 建立頁面，狀態設為 **Draft**
- 自動在頂部插入目錄區塊

### 3. 搬移至筆記庫

```
drafts/HTTP-Session.md → notes/10-Computer-Science/HTTP Session 管理機制：深度解析與安全實踐.md
```

- 根據 `category` 搬移到對應的分類目錄
- 在標題下方插入 `Updated: YYYY-MM-DD HH:MM` 時間戳

### 4. 更新 Notion 狀態

將 Notion 頁面狀態從 **Draft** 更新為 **Processed**，表示已成功歸檔。

若狀態更新失敗，系統會自動 **rollback**：將檔案從 `notes/` 移回 `drafts/`，重建 frontmatter，確保不會遺失任何草稿。

### 5. 部署網站

Git commit & push 後，觸發 VitePress 建置並部署至 GitHub Pages。

## 知識分類

| 代碼 | 分類 | 涵蓋範圍 |
|------|------|----------|
| `10-Computer-Science` | 電腦科學 | 資料結構、演算法、OS、網路、設計模式 |
| `12-AI-ML` | AI / ML | LLM 原理、Prompt Engineering、Token 機制、Agent 框架 |
| `15-Dev-Tools` | 開發工具 | 套件管理、版本控制、終端工具、IDE、CI/CD |
| `20-Finance` | 金融投資 | 財務分析、投資策略、加密貨幣、總經 |
| `30-Lifestyle` | 生活風格 | 生產力、健康、閱讀筆記、旅遊 |
| `40-News` | 時事新聞 | 科技動態、產業分析、重大事件 |
| `99-Inbox` | 收件匣 | 未歸類內容，待整理 |

## 專案結構

```
my-knowledge-base/
├── drafts/                  # 草稿放置區（自動處理後清空）
├── notes/                   # 已發布的知識筆記（依分類存放）
│   ├── 10-Computer-Science/
│   ├── 12-AI-ML/
│   ├── 15-Dev-Tools/
│   └── index.md             # VitePress 首頁
├── utils/                   # 核心 Python 模組
│   ├── draft_publisher.py   # 發布流程主程式
│   ├── md_to_notion.py      # Markdown → Notion Blocks 轉換器
│   ├── notion_reader.py     # Notion API 讀取操作
│   ├── notion_writer.py     # Notion API 寫入操作
│   ├── clients.py           # Notion Client 初始化
│   ├── categories.py        # 分類定義
│   ├── constants.py         # 常數設定
│   └── notion_languages.py  # 程式語言對應表（95+ 語言）
├── tools/                   # 開發除錯工具
│   ├── query_drafts.py      # 查詢 Notion 草稿頁面
│   └── test_md_convert.py   # 測試 Markdown 轉換結果
├── .github/workflows/
│   ├── publish-drafts.yml   # 自動發布 workflow（每小時 :30）
│   └── deploy.yml           # VitePress 建置 & GitHub Pages 部署
└── pyproject.toml           # Python 專案設定
```

## 技術棧

| 用途 | 技術 |
|------|------|
| Markdown 解析 | **mistune**（AST 模式） |
| Notion 同步 | **notion-client** 2.2.1 |
| 靜態網站 | **VitePress** 1.6.4 |
| 流程圖 | **Mermaid**（VitePress 插件） |
| CI/CD | **GitHub Actions** |
| 部署 | **GitHub Pages** |
| 語言 | Python 3.12+、Node.js 20 |

## 本地開發

### 環境設定

```bash
# 安裝 Python 依賴
pip install .

# 安裝 Node.js 依賴（VitePress）
npm install
```

### 環境變數

在 `utils/.env` 中設定：

```env
NOTION_TOKEN=ntn_your_notion_integration_token
NOTION_DATABASE_ID=your_database_uuid
```

### 手動發布草稿

```bash
python utils/draft_publisher.py
```

### 預覽網站

```bash
npm run docs:dev
```

### 開發工具

```bash
# 查詢 Notion 中的草稿頁面
python tools/query_drafts.py

# 查看特定頁面內容
python tools/query_drafts.py --content <PAGE_ID>

# 測試 Markdown 轉換結果
python tools/test_md_convert.py drafts/my-note.md

# 完整 JSON 輸出
python tools/test_md_convert.py drafts/my-note.md --json

# 篩選特定區塊類型
python tools/test_md_convert.py drafts/my-note.md --filter code
```

## Notion 資料庫欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| Name | Title | 頁面標題 |
| Status | Status | `Draft` → `Processed` → `Published` |
| Category | Select | 分類（與目錄對應） |
| Tags | Multi-select | 標籤 |
| Updated Time | Date | 發布時間（UTC+8） |

## 支援的 Markdown 語法

轉換至 Notion 時支援以下語法：

- **標題** `# H1` ~ `### H3`
- **段落** 含粗體、斜體、行內程式碼、刪除線、連結
- **程式碼區塊** 含語言標記（95+ 語言自動對應）
- **清單** 無序 / 有序，支援多層巢狀
- **表格** 原生 Notion 表格
- **引用區塊** `> blockquote`
- **分隔線** `---`
- **Mermaid 流程圖** 自動清理括號語法確保相容

## Future Plan

目前從 Claude.ai 生成 Markdown 到放入 `drafts/` 仍需手動操作：複製內容、建立檔案、git push。這是整條 pipeline 中唯一的人工環節。

### 目標：自動化「對話 → drafts/」的最後一哩路

```
現狀：Claude.ai /summary → 手動複製 → 手動 git push → drafts/
目標：Claude.ai /summary → 一鍵/自動 → drafts/
```

### 可能方向

- **Claude.ai MCP + GitHub Tool**：透過 MCP Server 讓 Claude.ai 對話中直接呼叫 GitHub API，將生成的 Markdown 自動 commit 至 `drafts/`，省去手動複製與 push 的步驟
- **Notion Web Clipper / API 反向流程**：在 Notion 端建立草稿頁面，透過 Webhook 或排程反向同步至 GitHub `drafts/`
- **iOS / macOS Shortcuts 整合**：搭配 Apple Shortcuts 快速將剪貼簿內容推送至 GitHub repo

最終目標是實現完全自動化的知識管道：**對話即筆記、筆記即發布**。

## License

MIT
