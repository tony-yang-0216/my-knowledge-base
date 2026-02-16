#!/usr/bin/env python3
"""查詢 Notion 資料庫中的 Draft 頁面清單與內容。"""
import argparse
import os
import sys

# 載入 utils/.env（確保從專案根目錄執行時也能讀取環境變數）
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'utils', '.env'))

# 加入 utils/ 目錄以匯入模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'utils'))

from notion_reader import get_draft_pages, get_page_content


def list_drafts():
    pages = get_draft_pages()
    if not pages:
        print("沒有找到任何 Draft 頁面。")
        return

    print(f"找到 {len(pages)} 個 Draft 頁面：\n")
    for page in pages:
        page_id = page["id"]
        title_parts = page.get("properties", {}).get("Name", {}).get("title", [])
        title = "".join(t.get("plain_text", "") for t in title_parts) or "(無標題)"
        created = page.get("created_time", "N/A")

        # 取得內容長度（透過 rich_text 長度估算）
        print(f"  ID: {page_id}")
        print(f"  標題: {title}")
        print(f"  建立時間: {created}")
        print()


def show_content(page_id):
    # 移除可能的連字號格式
    page_id = page_id.replace("-", "")
    content = get_page_content(page_id)
    if not content.strip():
        print(f"頁面 {page_id} 沒有內容。")
        return
    print(f"--- 頁面內容 ({len(content)} 字元) ---\n")
    print(content)


def main():
    parser = argparse.ArgumentParser(description="查詢 Notion Draft 頁面")
    parser.add_argument("--content", metavar="PAGE_ID",
                        help="查看特定頁面的完整 Markdown 內容")
    args = parser.parse_args()

    if args.content:
        show_content(args.content)
    else:
        list_drafts()


if __name__ == "__main__":
    main()
