---
name: test-md
description: 測試 Markdown 檔案經 mistune AST 轉換後的 Notion blocks 結構
allowed-tools: Bash(venv/bin/python tools/test_md_convert.py*)
---

# 測試 Markdown 轉 Notion Blocks

執行 `python tools/test_md_convert.py` 測試 Markdown 檔案經 mistune AST parser 轉換後產生的 Notion blocks 結構，不會實際上傳到 Notion。

## 使用方式

- **預設摘要輸出：** `venv/bin/python tools/test_md_convert.py <file.md>`
- **完整 JSON 輸出：** 加上 `--json` 參數
- **篩選特定類型 blocks：** 加上 `--filter <type>`（例如 `code`, `table`, `heading_2`）
- **從 stdin 讀取：** 省略檔案路徑，透過 pipe 傳入內容

## 行為

1. 根據使用者需求組合參數執行指令
2. 整理輸出結果，重點關注：
   - Block 統計與分佈
   - 潛在問題（超長 rich_text、空語言 code block）
   - 特定類型 blocks 的內容
3. 如果發現問題，提供修正建議
