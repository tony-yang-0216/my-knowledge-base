"""Notion write/update operations."""

from datetime import datetime
from clients import get_notion_client
from constants import NOTION_RICH_TEXT_LIMIT, NOTION_API_BATCH_SIZE, FALLBACK_CHUNK_SIZE, TW_TIMEZONE
from notion_reader import _paginate_blocks
from md_to_notion import markdown_to_notion_blocks


def _chunk_text(text, size=NOTION_RICH_TEXT_LIMIT):
    """將文字切成不超過 size 的片段（Notion rich_text 上限 2000 字元）"""
    return [text[i:i+size] for i in range(0, len(text), size)] or [""]


def chunk_raw_content(text, chunk_size=FALLBACK_CHUNK_SIZE):
    """單純將純文字切成片段，用於還原機制"""
    if not text:
        return ["(無內容)"]
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]


def append_blocks_batched(page_id, blocks):
    notion = get_notion_client()
    for start in range(0, len(blocks), NOTION_API_BATCH_SIZE):
        batch = blocks[start:start + NOTION_API_BATCH_SIZE]
        notion.blocks.children.append(block_id=page_id, children=batch)


def delete_all_blocks(page_id):
    """刪除頁面內的所有頂層區塊"""
    notion = get_notion_client()
    blocks = _paginate_blocks(page_id)
    for b in blocks:
        bid = b["id"]
        try:
            notion.blocks.delete(block_id=bid)
        except Exception as e:
            if "archived" in str(e).lower():
                continue
            else:
                print(f"⚠️ 刪除區塊 {bid} 時發生非預期錯誤: {e}")
                raise


def update_page_properties(page_id, ai_data):
    """
    最後的結案步驟：使用 AI 提取的專業標題更新 Notion 頁面屬性，
    包括狀態(Status)、分類(Category)、標籤(Tags)與更新時間。
    """
    notion = get_notion_client()
    try:
        # 取得台灣時間 (UTC+8) 的 ISO 8601 格式
        now = datetime.now(TW_TIMEZONE).strftime("%Y-%m-%dT%H:%M:%S+08:00")

        # 封裝要更新的屬性
        # 注意：這裡的 ai_data["title"] 是由 AI 根據內容分析後產出的專業標題
        props = {
            "Name": {"title": [{"text": {"content": ai_data["title"]}}]},
            "Status": {"status": {"name": "Processed"}},
            "Category": {"select": {"name": ai_data["category"]}},
            "Tags": {"multi_select": [{"name": tag} for tag in ai_data["tags"]]},
            "Updated Time": {"date": {"start": now}}
        }

        # 呼叫 Notion API 更新頁面屬性
        notion.pages.update(
            page_id=page_id,
            properties=props
        )
        print(f"✨ [Notion Properties] 屬性與標題更新成功: {page_id}")

    except Exception as e:
        print(f"❌ [Notion Properties] 更新失敗: {e}")
        # 向上拋出錯誤，讓 main() 標記此頁面處理未完成，以便下一小時重新嘗試
        raise


def update_notion_blocks_only(page_id, ai_data, raw_content):
    """
    僅更新 Notion 頁面的內容區塊 (Blocks)。
    如果失敗，會嘗試還原原始內容為純文字。
    """
    # 1. 預處理：失敗直接 raise，不執行 API 刪除 (避免空刪)
    try:
        content_blocks = markdown_to_notion_blocks(ai_data["content"], for_notion=True)
        # 插入 Notion 原生 TOC (Table of Contents) 在頁面最頂端
        toc_block = {
            "object": "block",
            "type": "table_of_contents",
            "table_of_contents": {"color": "default"}
        }
        content_blocks.insert(0, toc_block)
    except Exception as e:
        print(f"❌ [預處理] 失敗: {e}")
        raise

    # 2. API 操作：執行 刪除 -> 寫入
    try:
        delete_all_blocks(page_id)
        append_blocks_batched(page_id, content_blocks)
        print(f"✅ [Notion Blocks] 內容更新成功: {page_id}")
    except Exception as e:
        print(f"⚠️ [Notion API] 更新失敗，啟動還原機制。錯誤: {e}")
        try:
            text_chunks = chunk_raw_content(raw_content)
            fallback = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]}
                } for chunk in text_chunks
            ]
            append_blocks_batched(page_id, fallback)
            print("🔄 [Recovery] 原始內容已成功還原。")
        except Exception as recovery_error:
            print(f"🚨 [Fatal] 連還原也失敗了！頁面可能為空。錯誤: {recovery_error}")

        # 務必再次拋出錯誤，讓 main() 知曉並跳過後續 GitHub 存檔
        raise
