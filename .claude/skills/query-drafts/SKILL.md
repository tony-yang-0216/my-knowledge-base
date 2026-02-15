---
name: query-drafts
description: 查詢 Notion 資料庫中的 Draft 頁面清單與內容
allowed-tools: Bash(venv/bin/python tools/query_drafts.py*)
---

# 查詢 Notion Draft 頁面

執行 `python tools/query_drafts.py` 查詢 Notion 資料庫中所有狀態為 Draft 的頁面。

## 使用方式

- **列出所有草稿頁面：** 直接執行 `venv/bin/python tools/query_drafts.py`
- **查看特定頁面內容：** 如果使用者提供 page_id，執行 `venv/bin/python tools/query_drafts.py --content <page_id>`

## 行為

1. 執行對應的指令
2. 將結果整理為易讀的格式回覆使用者
3. 如果使用者想查看某頁內容，提示他們提供 page_id
