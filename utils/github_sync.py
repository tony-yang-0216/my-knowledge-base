"""Save AI-processed markdown to local repo (committed later by GitHub Action)."""

import os
from datetime import datetime
from constants import NOTES_DIR, TW_TIMEZONE
from md_to_notion import _sanitize_mermaid_in_markdown


def save_to_github(ai_result, content):
    """
    建立分類資料夾並將 AI 處理後的 Markdown 內容存檔至本地目錄（後續由 GitHub Action Commit）。
    """
    try:
        # 1. 確保分類資料夾存在
        category_dir = f"{NOTES_DIR}/{ai_result['category']}"
        os.makedirs(category_dir, exist_ok=True)

        # 2. 處理安全標題（移除檔案系統不允許的字元）
        safe_title = ai_result["title"].replace("/", "-").replace("\\", "-")
        file_path = f"{category_dir}/{safe_title}.md"

        # 3. 取得當前時間 (台灣時間)
        now = datetime.now(TW_TIMEZONE).strftime("%Y-%m-%d %H:%M")

        # 4. 在 H1 標題後插入 Updated Time 註記
        md_content = content
        content_lines = md_content.split('\n')
        if content_lines and content_lines[0].startswith('# '):
            # 在第一行 (# Title) 之後插入更新時間
            content_lines.insert(1, f'\n> Updated: {now}\n')
            md_content = '\n'.join(content_lines)

        # 5. Sanitize Mermaid 區塊（確保 GitHub 能正確渲染）
        md_content = _sanitize_mermaid_in_markdown(md_content)

        # 6. 寫入檔案
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        print(f"💾 [GitHub Sync] 檔案已寫入: {file_path}")
        return file_path

    except Exception as e:
        print(f"❌ [GitHub Sync] 檔案寫入失敗: {e}")
        raise  # 向上拋出錯誤，讓 main() 知曉並跳過後續的 Status 更新
