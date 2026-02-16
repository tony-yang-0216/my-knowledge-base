"""Orchestrator: processes Draft pages from Notion through AI and syncs to GitHub.

This module was decomposed from a monolith into focused modules.
Re-exports below preserve backward compatibility for tools/ scripts.
"""

import sys
import time
from constants import PAGE_DELAY_SECONDS
from notion_reader import get_draft_pages, get_page_content  # noqa: F401
from notion_writer import update_page_properties, update_notion_blocks_only
from ai_organizer import organize_with_ai
from github_sync import save_to_github
from md_to_notion import markdown_to_notion_blocks  # noqa: F401


def main():
    pages = get_draft_pages()
    print(f"找到 {len(pages)} 頁待處理...")

    # 紀錄是否有任何一頁失敗，用來決定最後 Workflow 的狀態
    has_any_error = False

    for page in pages:
        page_id = page["id"]
        try:
            raw_content = get_page_content(page_id)
            if not raw_content.strip():
                continue

            print(f"正在處理頁面: {page_id}，內容長度: {len(raw_content)} 字元")

            # A. AI 處理
            ai_result = organize_with_ai(raw_content)
            content = ai_result['content'].replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\').replace('\\t', '\t')
            ai_result['content'] = content

            # B. 更新 Notion 內容 (此時不改 Status，失敗會自動觸發 fallback)
            update_notion_blocks_only(page_id, ai_result, raw_content)

            # C. 存檔至 GitHub
            save_to_github(ai_result, content)

            # D. 最後一步：所有都成功了，才修改 Notion 屬性 (Status: Done)
            update_page_properties(page_id, ai_result)

            print(f"✅ 頁面 {page_id} 處理完成。")

        except Exception as e:
            print(f"❌ 處理頁面 {page_id} 時發生錯誤: {e}")
            has_any_error = True
            continue

        # 節流處理（每頁處理本身已包含多次 API 呼叫，自然有間隔）
        time.sleep(PAGE_DELAY_SECONDS)

    # 如果有任何一頁失敗，強制結束程式並拋出錯誤，讓 GitHub Actions 變紅燈
    if has_any_error:
        print("🚨 部分頁面處理失敗，請檢查 Log。")
        sys.exit(1)


if __name__ == "__main__":
    print("開始執行 Notion 筆記整理與同步流程...")
    main()
